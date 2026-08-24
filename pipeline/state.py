"""Estado persistente entre corridas: qué URLs ya se procesaron.

Evita que el mismo proyecto/noticia se vuelva a redactar en la corrida
siguiente sólo porque sigue apareciendo en los RSS.
"""
from __future__ import annotations

import json
from pathlib import Path

from .models import Candidate, now_iso

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "seen.json"


def load_seen() -> dict[str, dict]:
    if not STATE_PATH.exists():
        return {}
    with open(STATE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_seen(seen: dict[str, dict]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(seen, fh, ensure_ascii=False, indent=2, sort_keys=True)


def filter_unseen(candidates: list[Candidate], seen: dict[str, dict]) -> list[Candidate]:
    return [c for c in candidates if c.id not in seen]


def mark_seen(seen: dict[str, dict], candidates: list[Candidate], *, slug: str | None = None) -> None:
    for c in candidates:
        seen[c.id] = {"title": c.title, "url": c.url, "seen_at": now_iso(), "slug": slug}
