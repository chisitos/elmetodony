# -*- coding: utf-8 -*-
"""Artículos propios: uno por día, de lunes a viernes.

Por qué existe. El motor viejo curaba notas de medios extranjeros, y la
foto de esas notas era del medio, sin licencia: enlazarla no es republicar
con permiso. Hubo que retirar veintinueve. Escribir lo nuestro quita el
problema de raíz y, de paso, sirve más: una nota sobre porcelanato con
precios de Medellín y las tiendas donde verlo le resuelve algo a quien va
a remodelar aquí, cosa que no hace un apartamento en Roma.

Qué lo mantiene honesto:

- Los temas salen de config/temas.yaml, con su ángulo escrito de antemano.
  Sin ángulo no hay nota; es lo que evita el relleno.
- Las tiendas que se nombran salen del directorio real, con su dirección.
  No se inventa un almacén.
- Los precios se buscan en la web y se publican con el mes y el almacén
  donde se tomaron. Si la búsqueda no los encuentra, la nota sale sin
  precios: un precio inventado es peor que ninguno.
- Las entrevistas NO se generan. Poner una cita en boca de una persona
  real que no la dijo es una mentira. Para esas, `cuestionario()` arma las
  preguntas y el correo, y la nota se escribe cuando la persona responda.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path

import yaml

from .config import Config
from . import stock_images
from .llm import WEB_SEARCH_TOOL, call_json, call_json_mirando
from .models import Article, now_iso

log = logging.getLogger("remodelar.propios")

RAIZ = Path(__file__).resolve().parent.parent
TEMAS = RAIZ / "config" / "temas.yaml"
ESTADO = RAIZ / "data" / "temas_publicados.json"
ARTICLES_DIR = RAIZ / "data" / "articles"

# El tipo de tema se muestra como sección en el sitio.
SECCION = {
    "material": "Materiales",
    "guia": "Guías",
    "combinar": "Cómo combinar",
    "tendencia": "Tendencias",
    "inspiracion": "Inspiración",
    "entrevista": "Entrevistas",
}


def _cargar_temas() -> dict:
    return yaml.safe_load(TEMAS.read_text(encoding="utf-8"))


def _publicados() -> set[str]:
    # El estado va aparte y no dentro de temas.yaml: ese archivo está lleno
    # de comentarios que explican el plan, y reescribirlo con un volcado de
    # YAML los borraría todos.
    if ESTADO.exists():
        return set(json.loads(ESTADO.read_text(encoding="utf-8")))
    return set()


def _marcar(slug: str) -> None:
    hechos = _publicados() | {slug}
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(sorted(hechos), ensure_ascii=False, indent=2),
                      encoding="utf-8")


def pendientes(incluir_entrevistas: bool = False) -> list[dict]:
    plan = _cargar_temas()
    hechos = _publicados()
    return [t for t in plan["temas"]
            if t["slug"] not in hechos
            and (incluir_entrevistas or t["tipo"] != "entrevista")]


def _tiendas_para(tema: dict, directorio) -> list[dict]:
    """Almacenes reales del directorio para las categorías del tema.

    Se prefieren los de IDEO, que es el ancla comercial de la feria, pero
    sin dejar por fuera el resto: una nota que mande siempre al mismo
    centro comercial deja de ser útil y se nota.
    """
    vistos, salida = set(), []
    for cat in tema.get("categorias", []):
        for t in directorio.tiendas_de(cat):
            if t["slug"] in vistos:
                continue
            vistos.add(t["slug"])
            salida.append(t)
    salida.sort(key=lambda t: (not t.get("en_ideo"), t["nombre"]))
    return salida[:8]


def _sistema(cfg: Config, tema: dict, plan: dict) -> str:
    voz = cfg.raw.get("voice", {})
    principios = "\n".join("- " + p for p in voz.get("principles", []))
    prohibidas = ", ".join(voz.get("forbidden_phrases", []))
    minimo, maximo = voz.get("target_length_words", [600, 900])
    return f"""Usted escribe para Feria Remodelar, una revista de remodelación de
Medellín. El lector va a remodelar su casa y lo que busca es decidir bien
y no perder plata.

Esta nota es NUESTRA: no se cura ni se reescribe nada ajeno. Es un
{tema['tipo']} — {plan['pilares'][tema['tipo']]}

Reglas de voz:
{principios}

Nunca use estas palabras: {prohibidas}.
Extensión: entre {minimo} y {maximo} palabras.

Sobre los datos:
- No invente precios, marcas, normas ni citas.
- Si usa precios, diga el mes y el almacén donde se tomaron, y advierta
  que son de referencia.
- No le atribuya frases a ninguna persona real.
- Las tiendas que nombre tienen que ser de la lista que le paso. No
  agregue almacenes que no estén ahí, ni les invente dirección.

Formato del cuerpo (markdown sencillo): párrafos; `## ` para los
subtítulos; `**negrita**`; listas con `- `; tablas con `|` cuando compare
cosas; `[texto](url)` para enlaces. Nada de HTML.

Devuelva SOLO un objeto JSON con estas llaves:
  headline  — titular, sin dos puntos decorativos
  dek       — bajada de una o dos frases, que diga qué resuelve la nota
  body_md   — el cuerpo en markdown
  pull_quote— una frase del propio cuerpo para destacar
  tags       — entre tres y seis, en minúscula
  category  — exactamente "{SECCION[tema['tipo']]}"
"""


def _usuario(tema: dict, tiendas: list[dict], ruta: dict | None) -> str:
    lista = "\n".join(
        f"- {t['nombre']} — {t['direccion_completa']} ({t['zona_nombre']})"
        f"{' [en IDEO]' if t.get('en_ideo') else ''}: {t.get('aporta', '')}"
        for t in tiendas) or "(sin tiendas para este tema)"

    enlace = ""
    if ruta:
        enlace = (f"\n\nCierre mandando al lector a ver las cosas en persona, "
                  f"enlazando la ruta así: [{ruta['nombre']}](../rutas/{ruta['slug']}.html). "
                  f"Esa ruta tiene {ruta['total_paradas']} paradas.")

    precios = ("\n\nBusque en la web precios actuales en pesos colombianos en "
               "almacenes de Colombia (Homecenter, Corona, Sodimac u otros) y "
               "publíquelos con el mes y el almacén. Si no los encuentra, "
               "escriba la nota sin precios en vez de inventarlos."
               if tema.get("precios") else "")

    return f"""Tema: {tema['titulo']}

Ángulo que tiene que resolver:
{tema['angulo'].strip()}

Tiendas reales del directorio, para nombrar dónde verlo (use las que de
verdad apliquen, no todas):
{lista}{enlace}{precios}

Hoy es {date.today().isoformat()}."""


# La busqueda web devuelve el texto con sus marcas de cita pegadas
# (<cite index="12-6">$36.900</cite>). Si no se quitan salen crudas en la
# pagina: paso en la primera nota de porcelanato. Se conserva el texto
# citado, que es el dato; lo que sobra es la marca.
#
# El cierre se quita ANTES que la apertura: al reves, el patron de
# apertura encuentra el "cite>" que esta dentro de "</cite>" y deja un
# "</" suelto. Y no se toca el espacio de alrededor, porque comerselo
# pega la cifra a la palabra anterior ("cuesta$36.900").
_CITA_CIERRA = re.compile(r"</\s*cite\s*>")
_CITA_ABRE = re.compile(r"<\s*cite\b[^>]*>")


def _limpiar(texto: str) -> str:
    t = _CITA_ABRE.sub("", _CITA_CIERRA.sub("", texto or ""))
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def _slug(headline: str, usados: set[str]) -> str:
    from slugify import slugify
    base = f"{date.today().isoformat()}-{slugify(headline)[:70]}"
    s, n = base, 2
    while s in usados:
        s, n = f"{base}-{n}", n + 1
    return s


def escribir(tema: dict, cfg: Config, directorio) -> Article:
    plan = _cargar_temas()
    tiendas = _tiendas_para(tema, directorio)
    ruta = next((r for r in directorio.rutas if r["slug"] == tema.get("ruta")), None)

    raw = call_json(
        model=cfg.model("editor"),
        system=_sistema(cfg, tema, plan),
        user=_usuario(tema, tiendas, ruta),
        max_tokens=16000,
        tools=[WEB_SEARCH_TOOL] if tema.get("precios") else None,
    )
    if not isinstance(raw, dict):
        raise ValueError("El redactor no devolvió un objeto JSON")

    headline = _limpiar(re.sub(r"\s+", " ", str(raw["headline"])))
    usados = {p.stem for p in ARTICLES_DIR.glob("*.json")}

    return Article(
        slug=_slug(headline, usados),
        headline=headline,
        dek=_limpiar(str(raw.get("dek", ""))),
        body_md=_limpiar(str(raw.get("body_md", ""))),
        pull_quote=_limpiar(str(raw.get("pull_quote", ""))),
        tags=[str(t).strip().lower() for t in raw.get("tags", []) if str(t).strip()],
        category=str(raw.get("category", SECCION[tema["tipo"]])).strip(),
        source_name="Feria Remodelar",
        source_url="",
        published_at=now_iso(),
        original_published_at=None,
        es_propio=True,
        scores={},
        weighted_score=0.0,
        image_search_hint=tema.get("foto", ""),
    )


def cuestionario(tema: dict, cfg: Config) -> dict:
    """Preguntas y correo de contacto para una entrevista.

    No escribe la nota: la escribe una persona cuando reciba las
    respuestas. Aquí no se simula a nadie.
    """
    raw = call_json(
        model=cfg.model("editor"),
        system=("Usted prepara entrevistas para una revista de remodelación de "
                "Medellín. Escribe en español colombiano, de usted. Las "
                "preguntas son concretas y respondibles; nada de '¿qué opina "
                "del diseño?'. No redacte respuestas: no las tiene."),
        user=(f"Entrevista: {tema['titulo']}\n\nLo que debe sacar:\n"
              f"{tema['angulo'].strip()}\n\n"
              "Devuelva JSON con: preguntas (entre 8 y 12), correo (texto "
              "breve para pedir la entrevista) y quien_buscar (qué perfil de "
              "persona sirve para esta nota)."),
        max_tokens=4000,
    )
    return raw if isinstance(raw, dict) else {}


CATALOGO_PROPIO = RAIZ / "data" / "fotos_propias.json"


def _foto_propia(tema: dict) -> dict | None:
    """Una foto nuestra para el tema, si la hay.

    Se mira aqui ANTES de salir a un banco de imagenes. No es por ahorrar
    una llamada: los bancos libres no tienen interiores contemporaneos, y
    lo mejor que consiguieron para una nota de porcelanato fue una baldosa
    de barro. Una foto tomada en una tienda de Medellin le dice mas al
    lector, y ademas es nuestra.

    Se reparten por orden y no al azar, para que dos notas seguidas del
    mismo tema no abran con la misma imagen.
    """
    if not CATALOGO_PROPIO.exists():
        return None
    try:
        catalogo = json.loads(CATALOGO_PROPIO.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo leer el catalogo de fotos propias: %s", exc)
        return None

    # El tema de la foto se empareja con la ruta del articulo o con sus
    # categorias; la carpeta "cocinas" sirve para la nota de mesones.
    claves = {tema.get("ruta", ""), *tema.get("categorias", []), tema.get("slug", "")}
    candidatas = [c for c in catalogo
                  if any(k and (k in c["tema"] or c["tema"] in k) for k in claves)]
    if not candidatas:
        return None

    # Las apaisadas primero: la de apertura es horizontal.
    candidatas.sort(key=lambda c: (not c.get("apaisada"), c["url"]))
    usadas = {a.get("image_url", "") for a in _notas_existentes()}
    libres = [c for c in candidatas if c["url"] not in usadas]
    elegida = (libres or candidatas)[0]
    log.info("Foto propia para %s: %s", tema["slug"], elegida["url"])
    return elegida


def _notas_existentes() -> list[dict]:
    salida = []
    for f in ARTICLES_DIR.glob("*.json"):
        try:
            salida.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
    return salida


def _elegir_foto(tema: dict, art, cfg: Config) -> dict | None:
    """Escoge la foto MIRANDOLA, no por el orden del buscador.

    Openverse ordena por relevancia de texto, y el texto miente: para la
    nota de porcelanato la primera candidata era un patron azul abstracto
    llamado "iPhone Background - Ceramic", y el piso de porcelanato de
    verdad estaba de sexto. Ya habia pasado algo igual con el archivo
    impreso, cuando una nota de lavamanos abrio con una foto de una sala.

    Si ninguna sirve, devuelve None y la nota no se publica. Es preferible
    eso a una foto que no tiene nada que ver con lo que se esta leyendo.
    """
    cands = stock_images.candidatas(art.category, tema.get("foto", ""), cuantas=6)
    if not cands:
        return None

    miniaturas, validas = [], []
    for c in cands:
        datos = stock_images.miniatura(c.get("thumb") or c["url"])
        if datos:
            miniaturas.append(datos)
            validas.append(c)
    if not miniaturas:
        return None

    try:
        r = call_json_mirando(
            model=cfg.model("editor"),
            system=("Usted revisa fotos para una revista de remodelacion. Su "
                    "trabajo es que la foto corresponda con lo que dice la nota. "
                    "Una foto bonita que no es del tema no sirve."),
            user=(f"La nota se titula: {art.headline}\n"
                  f"Trata de: {tema['angulo'].strip()}\n\n"
                  "De las imagenes anteriores, cual sirve de foto de apertura? "
                  "Tiene que mostrar de verdad el material o el espacio del que "
                  "habla la nota. Descarte las abstractas, las de otro tema, las "
                  "que tengan texto o logos encima y las que corten una cara.\n\n"
                  'Responda JSON: {"elegida": <numero o null>, "razon": "<una frase>"}'),
            imagenes=miniaturas,
        )
    except Exception as exc:  # noqa: BLE001 - sin revision, mejor no publicar foto dudosa
        log.warning("No se pudo revisar las fotos de %s: %s", tema["slug"], exc)
        return None

    i = r.get("elegida") if isinstance(r, dict) else None
    if not isinstance(i, int) or not 0 <= i < len(validas):
        log.warning("Ninguna foto sirve para '%s': %s",
                    tema["slug"], (r or {}).get("razon", ""))
        return None
    log.info("Foto elegida para %s: %s", tema["slug"], r.get("razon", ""))
    return validas[i]


def run(n: int = 1) -> list[Path]:
    """Escribe las próximas n notas propias y las guarda."""
    from sitegen import directorio as dir_mod

    cfg = Config.load()
    directorio = dir_mod.load()
    escritos: list[Path] = []

    for tema in pendientes()[:n]:
        try:
            art = escribir(tema, cfg, directorio)
        except Exception as exc:  # noqa: BLE001 — que falle una no tumba el resto
            log.error("Falló la nota '%s': %s", tema["slug"], exc)
            continue

        # Foto: de Openverse, que filtra por licencia comercial y de
        # modificacion, y alojada aqui. La consulta sale del tema, escrita
        # en ingles, porque Openverse indexa casi todo en ingles.
        propia = _foto_propia(tema)
        if propia:
            art.image_url = propia["url"]
            art.image_credit = propia["credito"]
            art.image_license = ""
            art.image_source_url = ""
            # Es del archivo o de la feria, del tema pero no de este caso
            # puntual; el sitio lo dice en el pie.
            art.image_is_illustrative = True
            foto = None
        else:
            foto = _elegir_foto(tema, art, cfg)
        if foto:
            art.image_url = stock_images.alojar(foto["url"], art.slug, foto.get("thumb", "")) or ""
            art.image_credit = foto["credit"]
            art.image_license = foto["license"]
            art.image_source_url = foto["source_url"]
            # Es una foto del tema, no del lugar exacto del que habla la nota.
            art.image_is_illustrative = True

        if not art.image_url:
            log.warning("Sin foto publicable, no se publica: %s", tema["slug"])
            continue

        ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
        ruta = ARTICLES_DIR / f"{art.slug}.json"
        ruta.write_text(json.dumps(art.to_dict(), ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        _marcar(tema["slug"])
        escritos.append(ruta)
        log.info("Nota propia: %s -> %s", tema["slug"], art.slug)

    return escritos
