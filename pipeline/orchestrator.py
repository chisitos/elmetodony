"""Orquesta una corrida completa del pipeline editorial de Remodelar."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from . import curator, editor, state
from .config import Config
from .models import Article, Candidate
from .sources_rss import fetch_rss_candidates
from .sources_web import fetch_web_candidates

log = logging.getLogger("remodelar.orchestrator")
ARTICLES_DIR = Path(__file__).resolve().parent.parent / "data" / "articles"


def _dedup(candidates: list[Candidate]) -> list[Candidate]:
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    out: list[Candidate] = []
    for c in candidates:
        norm_title = " ".join(c.title.lower().split())
        if c.id in seen_ids or norm_title in seen_titles:
            continue
        seen_ids.add(c.id)
        seen_titles.add(norm_title)
        out.append(c)
    return out


def _persist(article: Article) -> Path:
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTICLES_DIR / f"{article.slug}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(article.to_dict(), fh, ensure_ascii=False, indent=2)
    return path


def _load_recent_articles(limit: int) -> list[Article]:
    """Lo último publicado — se le muestra al curador para que nunca repita
    la misma historia o el mismo ángulo en una edición nueva."""
    if not ARTICLES_DIR.exists():
        return []
    articles = []
    for path in ARTICLES_DIR.glob("*.json"):
        with open(path, "r", encoding="utf-8") as fh:
            articles.append(Article.from_dict(json.load(fh)))
    articles.sort(key=lambda a: a.published_at, reverse=True)
    return articles[:limit]


def run(cfg: Config | None = None) -> list[Path]:
    cfg = cfg or Config.load()
    seen = state.load_seen()

    rss_candidates = fetch_rss_candidates(cfg)
    web_candidates = fetch_web_candidates(cfg)
    candidates = _dedup(rss_candidates + web_candidates)
    candidates = state.filter_unseen(candidates, seen)

    log.info("Total candidatos nuevos tras dedup/estado: %d", len(candidates))
    if not candidates:
        log.info("Nada nuevo dentro de alcance. Corrida terminada sin artículos.")
        return []

    recent = _load_recent_articles(cfg.dedup_lookback_articles)
    scored = curator.curate(candidates, cfg, recent_published=recent)
    selected = [s for s in scored if s.selected]

    used_slugs = {p.stem for p in ARTICLES_DIR.glob("*.json")} if ARTICLES_DIR.exists() else set()
    written: list[Path] = []
    for sc in selected:
        try:
            article = editor.edit(sc, cfg, used_slugs)
        except Exception as exc:  # noqa: BLE001 — que un artículo falle no debe tumbar la corrida
            log.error("Falló la redacción de '%s': %s", sc.candidate.title[:60], exc)
            continue
        written.append(_persist(article))
        state.mark_seen(seen, [sc.candidate], slug=article.slug)

    # Marcamos como vistos también los candidatos evaluados pero no seleccionados,
    # para no volver a gastar tokens re-evaluándolos en la próxima corrida.
    unselected = [s.candidate for s in scored if not s.selected]
    state.mark_seen(seen, unselected)
    state.save_seen(seen)

    log.info("Corrida terminada: %d artículos nuevos publicados.", len(written))
    return written
