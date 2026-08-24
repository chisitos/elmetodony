"""Genera el sitio estático de ALBA a partir de data/articles/*.json."""
from __future__ import annotations

import html
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.config import Config  # noqa: E402
from pipeline.models import Article  # noqa: E402

log = logging.getLogger("alba.site")

ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = ROOT / "data" / "articles"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
OUTPUT_DIR = ROOT / "public"

_MESES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _human_date(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    return f"{dt.day} de {_MESES[dt.month]} de {dt.year}"


def _load_articles() -> list[Article]:
    if not ARTICLES_DIR.exists():
        return []
    articles = []
    for path in sorted(ARTICLES_DIR.glob("*.json")):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        articles.append(Article.from_dict(data))
    articles.sort(key=lambda a: a.published_at, reverse=True)
    return articles


def _body_html(body_md: str, pull_quote: str) -> str:
    paragraphs = [p.strip() for p in body_md.split("\n\n") if p.strip()]
    escaped = [html.escape(p) for p in paragraphs]
    if pull_quote and len(escaped) >= 2:
        mid = max(1, len(escaped) // 2)
        escaped.insert(mid, f"__QUOTE__{html.escape(pull_quote)}")
    parts = []
    for p in escaped:
        if p.startswith("__QUOTE__"):
            parts.append(f"<blockquote>{p[len('__QUOTE__'):]}</blockquote>")
        else:
            parts.append(f"<p>{p}</p>")
    return "\n".join(parts)


def build_site(*, asset_prefix: str = "") -> Path:
    """Renderiza public/index.html y public/articulos/<slug>.html.

    asset_prefix: prefijo relativo para links/estáticos (útil si se sirve
    desde un subpath). Por defecto vacío, sirve desde la raíz.
    """
    cfg = Config.load()
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    articles = _load_articles()
    view_models = []
    for a in articles:
        d = a.to_dict()
        d["published_at_human"] = _human_date(a.published_at)
        d["original_published_at_human"] = _human_date(a.original_published_at)
        view_models.append(d)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    articulos_dir = OUTPUT_DIR / "articulos"
    articulos_dir.mkdir(parents=True, exist_ok=True)

    common = dict(
        pub_name=cfg.publication_name,
        tagline=cfg.tagline,
        language=cfg.language,
        asset_prefix=asset_prefix,
        build_date=_human_date(datetime.utcnow().isoformat()),
    )

    index_tpl = env.get_template("index.html")
    index_html = index_tpl.render(
        featured=view_models[0] if view_models else None,
        rest=view_models[1:] if len(view_models) > 1 else view_models,
        **common,
    )
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")

    article_tpl = env.get_template("article.html")
    for a, vm in zip(articles, view_models):
        rendered = article_tpl.render(
            article=vm,
            body_html=_body_html(a.body_md, a.pull_quote),
            **{**common, "asset_prefix": "../" + asset_prefix if not asset_prefix else asset_prefix},
        )
        (articulos_dir / f"{a.slug}.html").write_text(rendered, encoding="utf-8")

    static_out = OUTPUT_DIR / "static"
    if static_out.exists():
        shutil.rmtree(static_out)
    shutil.copytree(STATIC_DIR, static_out)

    feed = [
        {
            "headline": a.headline,
            "dek": a.dek,
            "category": a.category,
            "tags": a.tags,
            "source_name": a.source_name,
            "source_url": a.source_url,
            "published_at": a.published_at,
            "url": f"articulos/{a.slug}.html",
        }
        for a in articles
    ]
    (OUTPUT_DIR / "feed.json").write_text(
        json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log.info("Sitio generado en %s (%d artículos)", OUTPUT_DIR, len(articles))
    return OUTPUT_DIR


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    build_site()
