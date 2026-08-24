"""Agente investigador de catálogo: lee RSS de medios de referencia.

No usa el modelo — es determinístico. Filtra por palabras clave de alcance
(config/editorial.yaml -> scope) y por fecha (lookback_days) antes de pasarle
candidatos al curador, para no gastar tokens en ruido evidente.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from html import unescape
import re

import feedparser

from .config import Config
from .models import Candidate

log = logging.getLogger("alba.sources_rss")

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return unescape(_TAG_RE.sub(" ", text or "")).strip()


def _entry_published_iso(entry) -> str | None:
    for key in ("published_parsed", "updated_parsed"):
        struct = getattr(entry, key, None)
        if struct:
            return datetime(*struct[:6], tzinfo=timezone.utc).isoformat(timespec="seconds")
    return None


def _matches_scope(text: str, cfg: Config) -> bool:
    lowered = text.lower()
    if cfg.exclude_keywords and any(k in lowered for k in cfg.exclude_keywords):
        return False
    if not cfg.include_keywords:
        return True
    return any(k in lowered for k in cfg.include_keywords)


def fetch_rss_candidates(cfg: Config) -> list[Candidate]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=cfg.lookback_days)
    candidates: list[Candidate] = []

    for feed in cfg.feeds:
        url = feed.get("url", "")
        name = feed.get("name", url)
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("No se pudo leer feed %s (%s): %s", name, url, exc)
            continue

        if getattr(parsed, "bozo", False) and not parsed.entries:
            log.warning("Feed %s vino vacío/mal formado: %s", name, url)
            continue

        count = 0
        for entry in parsed.entries:
            if count >= cfg.max_rss_per_feed:
                break
            title = _strip_html(getattr(entry, "title", ""))
            link = getattr(entry, "link", "")
            summary = _strip_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
            if not title or not link:
                continue

            published_iso = _entry_published_iso(entry)
            if published_iso:
                published_dt = datetime.fromisoformat(published_iso)
                if published_dt < cutoff:
                    continue

            if not _matches_scope(f"{title} {summary}", cfg):
                continue

            candidates.append(
                Candidate(
                    title=title,
                    url=link,
                    summary=summary[:1200],
                    source_name=name,
                    published_at=published_iso,
                    origin="rss",
                )
            )
            count += 1

    log.info("RSS: %d candidatos dentro de alcance y ventana de %dd", len(candidates), cfg.lookback_days)
    return candidates
