"""Agente investigador de exploración: busca en la web abierta con Claude.

Complementa al agente de RSS trayendo cosas que los feeds curados no cubren:
lanzamientos de materiales, ferias, tendencias que se están hablando pero
todavía no tienen nota en los medios de la lista fija.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from . import images
from .config import Config
from .llm import WEB_SEARCH_TOOL, call_json
from .models import Candidate

log = logging.getLogger("remodelar.sources_web")

SYSTEM = """Sos el agente investigador de exploración de Remodelar, un medio editorial \
vanguardista de arquitectura interior y remodelación de espacios, hecho para diseñadores \
(estilo designboom, pero con voz propia). Tu trabajo es usar búsqueda web para encontrar noticias, \
lanzamientos, proyectos y tendencias RECIENTES y VERIFICABLES en:
- arquitectura interior y remodelación de espacios residenciales/comerciales
- nuevos materiales y técnicas de construcción/acabado
- tendencias de la industria del diseño de interiores

Reglas estrictas:
- Sólo devolvés cosas que encontraste realmente en la búsqueda, con URL real y verificable.
- Nunca inventes una URL, una fecha o un dato. Si no estás seguro de la fecha, dejá el campo published_at en null.
- Priorizá fuentes de medios de diseño/arquitectura reconocidos, marcas y estudios, \
no blogs genéricos ni contenido publicitario disfrazado de noticia.
- Devolvé como máximo 10 candidatos, cada uno debe ser una historia distinta (no dupliques la misma nota vista en dos sitios).

Formato de salida: SOLO un array JSON (sin texto alrededor), cada elemento con esta forma exacta:
{"title": str, "url": str, "summary": str (2-4 frases, en español, resumiendo qué es y por qué importa),
 "source_name": str, "published_at": str ISO-8601 o null}
"""


def _user_prompt(cfg: Config) -> str:
    since = (date.today() - timedelta(days=cfg.lookback_days)).isoformat()
    return (
        f"Buscá noticias y novedades de arquitectura interior y remodelación de espacios "
        f"publicadas desde el {since} en adelante. Cubrí en tus búsquedas: proyectos de "
        f"remodelación destacados, nuevos materiales o técnicas de acabado, y tendencias de "
        f"la industria (ferias, informes, lanzamientos de marca). Hacé varias búsquedas "
        f"distintas antes de responder. Al final, respondé ÚNICAMENTE con el array JSON pedido."
    )


def fetch_web_candidates(cfg: Config) -> list[Candidate]:
    try:
        raw = call_json(
            model=cfg.model("research"),
            system=SYSTEM,
            user=_user_prompt(cfg),
            tools=[WEB_SEARCH_TOOL],
            max_tokens=6000,
            temperature=0.3,
        )
    except Exception as exc:  # noqa: BLE001 — la búsqueda web es un plus, no debe tumbar el pipeline
        log.warning("Agente de búsqueda web falló, sigo solo con RSS: %s", exc)
        return []

    if not isinstance(raw, list):
        log.warning("Agente de búsqueda web devolvió algo que no es una lista, lo descarto")
        return []

    candidates: list[Candidate] = []
    for item in raw:
        try:
            title = str(item["title"]).strip()
            url = str(item["url"]).strip()
        except (KeyError, TypeError):
            continue
        if not title or not url.startswith("http"):
            continue
        candidates.append(
            Candidate(
                title=title,
                url=url,
                summary=str(item.get("summary", "")).strip()[:1200],
                source_name=str(item.get("source_name", "Web")).strip() or "Web",
                published_at=item.get("published_at") or None,
                origin="web",
                image_url=images.fetch_og_image(url),
            )
        )

    log.info("Búsqueda web: %d candidatos", len(candidates))
    return candidates
