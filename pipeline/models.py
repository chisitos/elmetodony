"""Estructuras de datos que fluyen por el pipeline."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()[:16]


@dataclass
class Candidate:
    """Una noticia/tema crudo, antes de curar ni redactar."""

    title: str
    url: str
    summary: str
    source_name: str
    published_at: Optional[str] = None  # ISO 8601, puede ser None si no se sabe
    origin: str = "rss"  # "rss" | "web"
    image_url: Optional[str] = None

    @property
    def id(self) -> str:
        return _hash_url(self.url)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"id": self.id}


@dataclass
class ScoredCandidate:
    candidate: Candidate
    scores: dict[str, float]
    weighted_score: float
    rationale: str
    selected: bool


@dataclass
class Article:
    """Pieza final, redactada por el agente editor, lista para publicar."""

    slug: str
    headline: str
    dek: str
    body_md: str
    pull_quote: str
    tags: list[str]
    category: str
    source_name: str
    source_url: str
    published_at: str  # ISO 8601 — cuándo lo publica Remodelar
    original_published_at: Optional[str] = None
    # Firma del texto. En lo que viene de RSS no existe —se acredita al medio
    # en source_name—, pero el material propio de la revista impresa sí tiene
    # autor con nombre, y hay que darle crédito.
    autor: str = ""
    # Material propio: cambia cómo se acredita (firma y fotógrafo en vez de
    # "Imagen: {medio}") y permite alojar la foto en vez de enlazarla.
    es_propio: bool = False
    # Traducción autorizada por licencia. Sólo se publica si los tres campos
    # están, porque son los que hacen válida la autorización: sin licencia
    # verificable y sin enlace al original, no hay permiso que mostrar.
    # OJO: una licencia CC del texto NO cubre necesariamente sus fotos —
    # Brussels Studies, por ejemplo, dice "le texte seul". Por eso una nota
    # traducida nunca trae la foto del original.
    traducido_de: str = ""
    licencia_texto: str = ""
    url_original: str = ""
    scores: dict[str, float] = field(default_factory=dict)
    weighted_score: float = 0.0
    image_url: Optional[str] = None
    image_credit: str = ""
    # Cuando el candidato no trajo foto propia (ni de RSS ni de la fuente),
    # se completa con una foto de banco libre (pipeline/stock_images.py) —
    # genérica, con licencia CC, NUNCA una foto real de este proyecto puntual.
    # Estos tres campos distinguen ese caso para que el sitio nunca la
    # muestre como si documentara la obra descrita.
    image_is_illustrative: bool = False
    image_license: str = ""
    image_source_url: str = ""
    # Pista del editor (en inglés, ej. "closed kitchen glass partition") para
    # que, si hace falta banco libre, la foto sea del mismo tipo de espacio/
    # material que describe ESTA nota — no una genérica por categoría.
    image_search_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Article":
        return Article(**data)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
