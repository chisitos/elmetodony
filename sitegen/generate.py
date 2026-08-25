"""Genera el sitio estático de Remodelar a partir de data/articles/*.json.

Estructura de salida:
  public/index.html                 -> última edición (portada + grilla)
  public/ediciones/index.html       -> archivo de todas las ediciones
  public/ediciones/<year>-w<NN>.html -> cada edición pasada
  public/articulos/<slug>.html      -> cada nota individual
  public/static/                    -> CSS

Las "ediciones" agrupan los artículos por semana calendario (ISO) de
published_at. No es paginación infinita: cada semana es una selección
curada y cerrada — ver pipeline/curator.py.
"""
from __future__ import annotations

import html
import json
import logging
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.config import Config  # noqa: E402
from pipeline.models import Article  # noqa: E402

log = logging.getLogger("remodelar.site")

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


def _week_range_human(year: int, week: int) -> str:
    monday = date.fromisocalendar(year, week, 1)
    sunday = date.fromisocalendar(year, week, 7)
    if monday.month == sunday.month:
        return f"{monday.day}–{sunday.day} de {_MESES[monday.month]} de {sunday.year}"
    if monday.year == sunday.year:
        return f"{monday.day} de {_MESES[monday.month]} – {sunday.day} de {_MESES[sunday.month]} de {sunday.year}"
    return f"{monday.day} de {_MESES[monday.month]} de {monday.year} – {sunday.day} de {_MESES[sunday.month]} de {sunday.year}"


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


def _view_model(a: Article) -> dict:
    d = a.to_dict()
    d["published_at_human"] = _human_date(a.published_at)
    d["original_published_at_human"] = _human_date(a.original_published_at)
    return d


def _build_editions(view_models: list[dict]) -> list[dict]:
    """Agrupa por semana ISO de published_at y numera cronológicamente."""
    by_week: dict[tuple[int, int], list[dict]] = {}
    for vm in view_models:
        dt = datetime.fromisoformat(vm["published_at"].replace("Z", "+00:00"))
        year, week, _ = dt.isocalendar()
        by_week.setdefault((year, week), []).append(vm)

    editions = []
    for i, key in enumerate(sorted(by_week.keys()), start=1):
        year, week = key
        editions.append(
            {
                "number": i,
                "slug": f"{year}-w{week:02d}",
                "range_human": _week_range_human(year, week),
                # ya vienen ordenados desc (view_models global ya está desc)
                "articles": by_week[key],
            }
        )
    editions.sort(key=lambda e: e["number"], reverse=True)
    return editions


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


def build_site() -> Path:
    cfg = Config.load()
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    articles = _load_articles()
    view_models = [_view_model(a) for a in articles]
    editions = _build_editions(view_models)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    articulos_dir = OUTPUT_DIR / "articulos"
    ediciones_dir = OUTPUT_DIR / "ediciones"
    articulos_dir.mkdir(parents=True, exist_ok=True)
    ediciones_dir.mkdir(parents=True, exist_ok=True)

    common = dict(
        pub_name=cfg.publication_name,
        tagline=cfg.tagline,
        language=cfg.language,
        build_date=_human_date(datetime.utcnow().isoformat()),
    )

    def render(template_name: str, output_path: Path, depth: int, **ctx) -> None:
        tpl = env.get_template(template_name)
        rendered = tpl.render(asset_prefix="../" * depth, **common, **ctx)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")

    # Portada = última edición
    if editions:
        render("edition.html", OUTPUT_DIR / "index.html", depth=0, edition=editions[0], is_latest=True)
    else:
        render("editions_archive.html", OUTPUT_DIR / "index.html", depth=0, editions=[])

    # Archivo de ediciones
    render("editions_archive.html", ediciones_dir / "index.html", depth=1, editions=editions)

    # Cada edición pasada (todas, incluida la última, para que también tenga URL propia)
    for e in editions:
        render("edition.html", ediciones_dir / f"{e['slug']}.html", depth=1, edition=e, is_latest=(e is editions[0]))

    # Cada artículo
    article_tpl = env.get_template("article.html")
    for a, vm in zip(articles, view_models):
        rendered = article_tpl.render(
            article=vm,
            body_html=_body_html(a.body_md, a.pull_quote),
            asset_prefix="../",
            **common,
        )
        (articulos_dir / f"{a.slug}.html").write_text(rendered, encoding="utf-8")

    static_out = OUTPUT_DIR / "static"
    if static_out.exists():
        shutil.rmtree(static_out)
    shutil.copytree(STATIC_DIR, static_out)

    # Sin esto, GitHub Pages puede correr el sitio a través de Jekyll y
    # tropezar con nombres que empiezan con "_" (no tenemos ninguno hoy,
    # pero es la convención estándar para un sitio estático que no es un
    # sitio Jekyll).
    (OUTPUT_DIR / ".nojekyll").touch()

    feed = [
        {
            "headline": a.headline,
            "dek": a.dek,
            "category": a.category,
            "tags": a.tags,
            "source_name": a.source_name,
            "source_url": a.source_url,
            "published_at": a.published_at,
            "image_url": a.image_url,
            "url": f"articulos/{a.slug}.html",
        }
        for a in articles
    ]
    (OUTPUT_DIR / "feed.json").write_text(
        json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log.info(
        "Sitio generado en %s (%d artículos, %d ediciones)",
        OUTPUT_DIR,
        len(articles),
        len(editions),
    )
    return OUTPUT_DIR


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    build_site()
