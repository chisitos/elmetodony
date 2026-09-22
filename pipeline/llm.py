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
    retries: int = 3,
) -> Any:
    """Llama al modelo pidiendo una respuesta JSON y la parsea.

    Si `tools` incluye la tool de búsqueda web, el modelo puede hacer varias
    idas y vueltas de tool-use antes de devolver el JSON final; acá sólo nos
    interesa el texto de la última respuesta.

    Sin `temperature`: los modelos Claude 5 la rechazan con un 400
    ("`temperature` is deprecated for this model"). El control del tono no se
    pierde — vive donde siempre estuvo, en la guía de voz que
    `config/editorial.yaml` inyecta en el system prompt de cada agente.
    """
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            kwargs: dict[str, Any] = dict(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            if tools:
                kwargs["tools"] = tools
            # Streaming siempre: con techos de tokens altos (los que necesita el
            # razonamiento de Claude 5) el SDK rechaza el modo normal — "Streaming
            # is required for operations that may take longer than 10 minutes".
            # No cambia el resultado: se espera igual el mensaje completo.
            with client().messages.stream(**kwargs) as stream:
                resp = stream.get_final_message()
            # Los modelos Claude 5 razonan antes de responder: la respuesta trae
            # bloques `thinking` además del `text`. Acá sólo nos sirve el texto,
            # pero el razonamiento SÍ consume `max_tokens` — por eso el techo
            # tiene que cubrir las dos cosas, no sólo el JSON de salida.
            text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
            text = "\n".join(text_parts).strip()
            if not text:
                tipos = [getattr(b, "type", "?") for b in resp.content] or ["(sin bloques)"]
                if resp.stop_reason == "max_tokens":
                    raise ValueError(
                        f"El modelo se quedó sin presupuesto antes de escribir la respuesta "
                        f"(max_tokens={max_tokens}, bloques devueltos: {', '.join(tipos)}). "
                        f"Subí max_tokens en el agente que hizo esta llamada."
                    )
                raise ValueError(
                    f"Respuesta sin texto (stop_reason={resp.stop_reason}, "
                    f"bloques: {', '.join(tipos)})"
                )
            return _extract_json(text)
        except Exception as exc:  # noqa: BLE001 — reintentamos cualquier falla transitoria
            last_err = exc
            # Un pedido mal formado, una clave inválida o un permiso faltante no
            # se arreglan esperando: reintentar sólo quema tiempo y esconde el
            # error real tres capas más abajo.
            status = getattr(exc, "status_code", None)
            if status in (400, 401, 403, 404, 422):
                raise RuntimeError(f"La API rechazó el pedido ({status}): {exc}") from exc
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
