"""Genera el sitio estático de Remodelar.

Dos mitades que comparten plantilla y hoja de estilo:

  DIRECTORIO Y RUTAS — el producto. Sale de data/tiendas.yaml y
  config/rutas.yaml (ver sitegen/directorio.py).
      public/index.html                  -> portada
      public/rutas/index.html            -> todas las rutas
      public/rutas/<slug>.html           -> una ruta, paso a paso
      public/directorio/index.html       -> buscador
      public/directorio/<slug>.html      -> ficha de tienda
      public/ideo/index.html             -> el ancla

  REVISTA — el motor editorial semanal que ya existía. Sale de
  data/articles/*.json y sigue igual, sólo que colgada de /revista/.
      public/revista/index.html          -> última edición
      public/ediciones/index.html        -> archivo
      public/ediciones/<year>-w<NN>.html -> cada edición
      public/articulos/<slug>.html       -> cada nota

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
from sitegen import directorio  # noqa: E402

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


def _manifest(sitio: dict) -> str:
    """manifest.webmanifest — lo que hace que el sitio se instale en la
    pantalla de inicio. La ruta se hace caminando, así que vale la pena."""
    return json.dumps(
        {
            "name": f"{sitio.get('nombre', 'Remodelar')} — {sitio.get('tagline', '')}",
            "short_name": sitio.get("nombre", "Remodelar"),
            "description": sitio.get("descripcion", ""),
            "start_url": "./index.html",
            "scope": "./",
            "display": "standalone",
            "orientation": "portrait",
            "background_color": "#ffffff",
            "theme_color": "#0a0a0a",
            "lang": "es",
            "icons": [
                {
                    "src": "static/icono.svg",
                    "sizes": "any",
                    "type": "image/svg+xml",
                    "purpose": "any",
                }
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def build_site() -> Path:
    cfg = Config.load()
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    dir_data = directorio.load()

    articles = _load_articles()
    view_models = [_view_model(a) for a in articles]
    editions = _build_editions(view_models)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    articulos_dir = OUTPUT_DIR / "articulos"
    ediciones_dir = OUTPUT_DIR / "ediciones"
    rutas_dir = OUTPUT_DIR / "rutas"
    tiendas_dir = OUTPUT_DIR / "directorio"
    for d in (articulos_dir, ediciones_dir, rutas_dir, tiendas_dir, OUTPUT_DIR / "revista", OUTPUT_DIR / "ideo"):
        d.mkdir(parents=True, exist_ok=True)

    sitio = dir_data.sitio
    ancla = dir_data.ancla
    ciudad = sitio.get("ciudad", "Medellín")

    # Conteos por categoría y por zona — se usan en los chips del buscador y
    # en el mosaico de la portada, para que nadie toque un filtro vacío.
    cats_con_n = []
    for c in dir_data.categorias:
        n = len(dir_data.tiendas_de(c["slug"]))
        if n:
            cats_con_n.append({**c, "n": n})

    zonas_con_n = []
    for z in dir_data.zonas:
        n = sum(1 for t in dir_data.tiendas if t.get("zona") == z["slug"])
        if n:
            zonas_con_n.append({**z, "n": n})

    # Va en toda página: la navegación y el pie se arman con esto.
    common = dict(
        pub_name=cfg.publication_name,
        tagline=sitio.get("tagline", cfg.tagline),
        language=cfg.language,
        build_date=_human_date(datetime.utcnow().isoformat()),
        ciudad=ciudad,
        sitio=sitio,
        ancla=ancla,
        ancla_maps_url=directorio.maps_url(ancla.get("direccion", "")),
        n_tiendas=len(dir_data.tiendas),
        n_rutas=len(dir_data.rutas),
        n_ideo=len(dir_data.tiendas_ideo),
        nav_rutas=dir_data.rutas[:6],
        # El lateral lleva sólo cuatro rutas, con miniatura: es un atajo, no
        # el índice completo (ése vive en /rutas/).
        nav_rutas_side=dir_data.rutas[:4],
        nav_categorias=cats_con_n,
        nav_ruta=None,
    )

    def render(template_name: str, output_path: Path, depth: int, **ctx) -> None:
        tpl = env.get_template(template_name)
        base = dict(common)
        base.update(ctx)
        rendered = tpl.render(asset_prefix="../" * depth, **base)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")

    # ---- Portada -----------------------------------------------------------
    render(
        "home.html",
        OUTPUT_DIR / "index.html",
        depth=0,
        nav_active="inicio",
        # La portada la abre la última edición: es lo único del sitio con
        # fotografía propia del motor editorial, con crédito a cada fuente.
        edicion=editions[0] if editions else None,
        rutas_destacadas=dir_data.rutas[:6],
        categorias=cats_con_n,
    )

    # ---- Rutas -------------------------------------------------------------
    render("rutas_index.html", rutas_dir / "index.html", depth=1, nav_active="rutas", rutas=dir_data.rutas)

    for r in dir_data.rutas:
        otras = [o for o in dir_data.rutas if o["slug"] != r["slug"]][:3]
        render("ruta.html", rutas_dir / f"{r['slug']}.html", depth=1,
               nav_active="rutas", nav_ruta=r["slug"], ruta=r, otras_rutas=otras)

    # ---- Directorio --------------------------------------------------------
    render(
        "directorio.html",
        tiendas_dir / "index.html",
        depth=1,
        nav_active="directorio",
        tiendas=dir_data.tiendas,
        categorias=cats_con_n,
        zonas_con_tiendas=zonas_con_n,
    )

    for t in dir_data.tiendas:
        cats_full = [dir_data.cat_por_slug[c] for c in t.get("categorias", []) if c in dir_data.cat_por_slug]
        if t.get("en_ideo"):
            otras_ideo = [o for o in dir_data.tiendas_ideo if o["slug"] != t["slug"]]
            cercanas = []
        else:
            otras_ideo = []
            cercanas = [
                o for o in dir_data.tiendas
                if o.get("zona") == t.get("zona") and o["slug"] != t["slug"]
            ][:6]
        render(
            "tienda.html",
            tiendas_dir / f"{t['slug']}.html",
            depth=1,
            nav_active="directorio",
            t={**t, "cats_full": cats_full},
            otras_ideo=otras_ideo,
            cercanas=cercanas,
        )

    # ---- IDEO --------------------------------------------------------------
    render(
        "ideo.html",
        OUTPUT_DIR / "ideo" / "index.html",
        depth=1,
        nav_active="ideo",
        tiendas_ideo=dir_data.tiendas_ideo,
        rutas_ideo=[r for r in dir_data.rutas if r["paradas_ideo"]][:6],
    )

    # ---- Revista (el motor editorial que ya existía) -----------------------
    if editions:
        render("edition.html", OUTPUT_DIR / "revista" / "index.html", depth=1,
               nav_active="revista", edition=editions[0], is_latest=True)
    else:
        render("editions_archive.html", OUTPUT_DIR / "revista" / "index.html", depth=1,
               nav_active="revista", editions=[])

    render("editions_archive.html", ediciones_dir / "index.html", depth=1,
           nav_active="revista", editions=editions)

    for e in editions:
        render("edition.html", ediciones_dir / f"{e['slug']}.html", depth=1,
               nav_active="revista", edition=e, is_latest=(e is editions[0]))

    article_tpl = env.get_template("article.html")
    for a, vm in zip(articles, view_models):
        ctx = dict(common)
        ctx.update(nav_active="revista", article=vm,
                   body_html=_body_html(a.body_md, a.pull_quote), asset_prefix="../")
        (articulos_dir / f"{a.slug}.html").write_text(article_tpl.render(**ctx), encoding="utf-8")

    # ---- Estáticos y PWA ---------------------------------------------------
    static_out = OUTPUT_DIR / "static"
    if static_out.exists():
        shutil.rmtree(static_out)
    shutil.copytree(STATIC_DIR, static_out)

    # El service worker tiene que quedar en la raíz: su alcance es el
    # directorio donde vive, y desde /static/ no podría cachear el sitio.
    shutil.copy(STATIC_DIR / "sw.js", OUTPUT_DIR / "sw.js")
    (OUTPUT_DIR / "manifest.webmanifest").write_text(_manifest(sitio), encoding="utf-8")

    # Búsqueda: JSON con todo el directorio, por si más adelante se quiere
    # consumir desde otro lado (mapa, app, integración con IDEO).
    (OUTPUT_DIR / "directorio.json").write_text(
        json.dumps(
            [
                {k: v for k, v in t.items() if k not in ("buscable", "rutas")}
                for t in dir_data.tiendas
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

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
        "Sitio generado en %s — %d tiendas (%d en IDEO), %d rutas, %d artículos, %d ediciones",
        OUTPUT_DIR,
        len(dir_data.tiendas),
        len(dir_data.tiendas_ideo),
        len(dir_data.rutas),
        len(articles),
        len(editions),
    )
    return OUTPUT_DIR


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    build_site()
