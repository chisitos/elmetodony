"""Wrapper delgado sobre el SDK de Anthropic para los agentes del pipeline.

Requiere ANTHROPIC_API_KEY en el entorno. No usamos ningún framework de
agentes: cada "agente" es simplemente un rol (system prompt) + una llamada
a la API, con o sin la tool de búsqueda web nativa.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Optional

import anthropic

_client: Optional[anthropic.Anthropic] = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta ANTHROPIC_API_KEY en el entorno. "
                "En GitHub Actions: configurala como secret del repo."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _extract_json(text: str) -> Any:
    """Extrae el primer bloque JSON (objeto o arreglo) de una respuesta de texto."""
    text = text.strip()
    # Caso feliz: la respuesta entera es JSON.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Buscar un bloque ```json ... ``` o el primer {...}/[...] balanceado.
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    chunk = text[start : i + 1]
                    try:
                        return json.loads(chunk)
                    except json.JSONDecodeError:
                        break
    raise ValueError(f"No se pudo extraer JSON de la respuesta del modelo:\n{text[:800]}")


def call_json(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 4096,
    tools: Optional[list[dict]] = None,
    temperature: float = 0.4,
    retries: int = 3,
) -> Any:
    """Llama al modelo pidiendo una respuesta JSON y la parsea.

    Si `tools` incluye la tool de búsqueda web, el modelo puede hacer varias
    idas y vueltas de tool-use antes de devolver el JSON final; acá sólo nos
    interesa el texto de la última respuesta.
    """
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            kwargs: dict[str, Any] = dict(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            if tools:
                kwargs["tools"] = tools
            resp = client().messages.create(**kwargs)
            text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
            text = "\n".join(text_parts).strip()
            if not text:
                raise ValueError("Respuesta vacía del modelo")
            return _extract_json(text)
        except Exception as exc:  # noqa: BLE001 — reintentamos cualquier falla transitoria
            last_err = exc
            if attempt < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"Falló la llamada al modelo tras {retries} intentos: {last_err}") from last_err


# Tool de búsqueda web nativa de Anthropic. Se declara acá para no repetir
# el nombre/versión de la tool en cada agente que la usa.
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 6,
}
