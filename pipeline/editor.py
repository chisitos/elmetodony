"""Agente editor: reescribe el candidato seleccionado con la voz de Remodelar."""
from __future__ import annotations

import logging
import re
from datetime import date

from slugify import slugify

from .config import Config
from .llm import call_json
from .models import Article, ScoredCandidate, now_iso

log = logging.getLogger("remodelar.editor")

SYSTEM_TEMPLATE = """Sos el/la editor/a en jefe de Remodelar, un medio editorial vanguardista \
de arquitectura interior y remodelación de espacios, hecho para diseñadores (pensalo como \
un cruce entre designboom y una revista de autor: mirada de vanguardia, pero rigurosa con \
los datos).

Tu voz, sin excepción:
{principles}

Frases prohibidas (no las uses bajo ningún concepto): {forbidden}

Extensión objetivo del cuerpo: entre {min_words} y {max_words} palabras.

Vas a recibir UNA noticia/proyecto ya seleccionado por el equipo curatorial, con su \
resumen y fuente. Tu trabajo es reescribirlo como una pieza editorial ORIGINAL en la \
voz de Remodelar — no traducir ni parafrasear línea por línea, sino producir una lectura \
propia del hecho, fundamentada estrictamente en la información dada. Si el resumen no \
alcanza para un dato (por ejemplo el precio, o el m2 exacto), no lo inventes: omitilo \
o hablá en términos generales.

Además, en "image_search_query" describí en inglés, en 3 a 6 palabras, el \
tipo de espacio/material/elemento concreto del que habla la nota (no el \
proyecto puntual — una foto de banco libre nunca va a ser la obra real, así \
que el objetivo es que sea del MISMO tipo de espacio, no de un tema \
genérico). Ejemplos de la precisión que buscamos: si la nota es sobre una \
cocina cerrada con puerta de vidrio, "closed kitchen glass partition door" \
y no "residential interior design"; si es sobre terrazo reciclado, \
"terrazzo flooring recycled aggregate" y no "building material texture"; \
si es sobre iluminación circadiana en oficinas, "warm office lighting \
interior" y no "interior lighting design". Cuanto más específico a la \
nota puntual, mejor — evitá términos genéricos si el texto te da algo \
más concreto para usar.

Formato de salida: SOLO un objeto JSON (sin texto alrededor), con esta forma exacta:
{{"headline": str (en español, directo, sin gancho de clickbait, máx 90 caracteres),
  "dek": str (bajada de 1 frase que amplía el título, máx 160 caracteres),
  "body_md": str (el cuerpo del artículo en markdown simple: párrafos separados por \\n\\n, \
sin subtítulos ni listas salvo que aporten mucho),
  "pull_quote": str (una frase del propio cuerpo, la más filosa, para destacar como cita),
  "tags": [str] (3 a 5 tags cortos en minúscula, ej: "reforma", "hormigón", "iluminación"),
  "category": str (una sola categoría: "Remodelación", "Materiales", "Tendencias", \
"Interiorismo residencial", "Interiorismo comercial", o "Iluminación"),
  "image_search_query": str (en inglés, 3-6 palabras, ver instrucción arriba)}}
"""


def _build_system(cfg: Config) -> str:
    lo, hi = cfg.target_length_words
    return SYSTEM_TEMPLATE.format(
        principles="\n".join(f"- {p}" for p in cfg.voice_principles),
        forbidden=", ".join(cfg.forbidden_phrases),
        min_words=lo,
        max_words=hi,
    )


def _user_prompt(sc: ScoredCandidate) -> str:
    c = sc.candidate
    return (
        f"Fuente: {c.source_name}\n"
        f"URL original: {c.url}\n"
        f"Fecha original: {c.published_at or 'desconocida'}\n"
        f"Título original: {c.title}\n"
        f"Resumen/material disponible:\n{c.summary}\n\n"
        f"Por qué lo seleccionó el equipo curatorial: {sc.rationale}\n"
    )


def _unique_slug(headline: str, used_slugs: set[str]) -> str:
    base = slugify(headline)[:80] or "articulo"
    slug = base
    n = 2
    while slug in used_slugs:
        slug = f"{base}-{n}"
        n += 1
    used_slugs.add(slug)
    return slug


def edit(sc: ScoredCandidate, cfg: Config, used_slugs: set[str]) -> Article:
    raw = call_json(
        model=cfg.model("editor"),
        system=_build_system(cfg),
        user=_user_prompt(sc),
        max_tokens=3000,
        temperature=0.7,
    )
    if not isinstance(raw, dict):
        raise ValueError("El editor no devolvió un objeto JSON")

    headline = re.sub(r"\s+", " ", str(raw["headline"]).strip())
    slug_base = f"{date.today().isoformat()}-{headline}"

    article = Article(
        slug=_unique_slug(slug_base, used_slugs),
        headline=headline,
        dek=str(raw.get("dek", "")).strip(),
        body_md=str(raw.get("body_md", "")).strip(),
        pull_quote=str(raw.get("pull_quote", "")).strip(),
        tags=[str(t).strip().lower() for t in raw.get("tags", []) if str(t).strip()],
        category=str(raw.get("category", "Tendencias")).strip(),
        source_name=sc.candidate.source_name,
        source_url=sc.candidate.url,
        published_at=now_iso(),
        original_published_at=sc.candidate.published_at,
        scores=sc.scores,
        weighted_score=sc.weighted_score,
        image_url=sc.candidate.image_url,
        image_credit=sc.candidate.source_name,
        image_search_hint=str(raw.get("image_search_query", "")).strip(),
    )
    log.info("Editor: '%s' -> %s", sc.candidate.title[:60], article.slug)
    return article
