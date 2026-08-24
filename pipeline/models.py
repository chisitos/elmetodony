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
    scores: dict[str, float] = field(default_factory=dict)
    weighted_score: float = 0.0
    image_url: Optional[str] = None
    image_credit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Article":
        return Article(**data)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
