"""Orquesta una corrida completa del pipeline editorial de Remodelar."""
from __future__ import annotations

import json

import requests
import logging
from pathlib import Path

from . import curator, editor, stock_images, state
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


def _alojar(url: str, slug: str) -> str:
    """Baja la foto con licencia y la guarda aqui, en JPEG y al ancho del
    sitio. Enlazarla dejaria la portada a merced de un servidor ajeno, y le
    cargaria a el nuestro trafico."""
    import io

    from PIL import Image

    destino_dir = Path(__file__).resolve().parent.parent / "sitegen" / "static" / "libres"
    try:
        resp = requests.get(url, timeout=30,
                            headers={"User-Agent": "FeriaRemodelar/1.0 (+https://feriaremodelar.com)"})
        resp.raise_for_status()
        im = Image.open(io.BytesIO(resp.content))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        if im.width > 1400:
            im.thumbnail((1400, 4200), Image.LANCZOS)
        destino_dir.mkdir(parents=True, exist_ok=True)
        im.save(destino_dir / (slug + ".jpg"), "JPEG", quality=82,
                optimize=True, progressive=True)
        return "static/libres/" + slug + ".jpg"
    except Exception as exc:  # noqa: BLE001 - que falle bajarla no tumba la corrida
        log.warning("No se pudo alojar la foto de %s: %s", slug, exc)
        return ""


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

        # La foto que trae el candidato es la del medio original y no tiene
        # licencia: enlazarla no es republicar con permiso, es usar su
        # imagen y su servidor. Se descarta SIEMPRE, y asi el respaldo de
        # Openverse -que si filtra por licencia- alcanza a actuar. Antes
        # nunca actuaba, porque este campo ya venia lleno.
        if article.image_url and not article.image_license:
            log.info("Foto sin licencia descartada en %s: %s",
                     article.slug, article.image_url[:70])
            article.image_url = ""
            article.image_credit = ""
            article.image_source_url = ""

        if not article.image_url:
            stock = stock_images.search_illustrative_image(article.category, article.image_search_hint)
            if stock:
                article.image_url = _alojar(stock["url"], article.slug) or stock["url"]
                article.image_credit = stock["credit"]
                article.image_license = stock["license"]
                article.image_source_url = stock["source_url"]
                article.image_is_illustrative = True
                log.info("Nota sin foto propia, completada con imagen ilustrativa: %s", article.slug)

        # Sin foto que podamos publicar, la nota no sale. Es preferible una
        # revista corta a una con notas deslucidas o con fotos ajenas.
        if not article.image_url:
            log.warning("Sin foto publicable, no se publica: %s", article.slug)
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
