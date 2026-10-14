"""Fallback de imagen ilustrativa vía Openverse, para cuando el candidato no
trajo foto propia (ni del RSS ni de la fuente).

Diferencia clave con `pipeline/images.py`: esto NUNCA es una foto del
proyecto/objeto real descrito en la nota — es una foto genérica de banco
libre. Por eso el sitio la marca siempre como "imagen ilustrativa" y nunca
la mezcla visualmente con una foto real de la obra (ver
`image_is_illustrative` en pipeline/models.py). Pero "genérica" no quiere
decir cualquiera: tiene que ser del MISMO TIPO de espacio/material que
describe la nota (una cocina para una nota de cocinas, terrazo para una
nota de terrazo) — nunca una foto de arquitectura cualquiera puesta de
relleno. Por eso el agente editor manda su propia `image_search_query`
específica (ej. "closed kitchen glass partition"), y esta búsqueda la usa
como primer intento; el mapeo por categoría de acá abajo es sólo el
respaldo genérico si esa búsqueda puntual no encuentra nada.

Openverse (openverse.org, proyecto de Creative Commons) agrega fotos con
licencia abierta de Flickr, Wikimedia Commons, museos, etc., con su
metadata de licencia/autor/fuente. La API pública no requiere API key.
Filtramos a `license_type=commercial,modification` — sólo licencias que
permiten uso comercial y modificación (CC0, CC-BY, CC-BY-SA, dominio
público; quedan afuera las variantes NC/ND), y siempre guardamos autor,
licencia y link a la fuente para atribuir correctamente.
"""
from __future__ import annotations

import logging
import pathlib
from typing import Optional

import requests

log = logging.getLogger("remodelar.stock_images")

_API_URL = "https://api.openverse.org/v1/images/"
# Para la API basta identificarse. Para bajar la imagen no: Flickr
# devuelve 403 a todo lo que diga "bot" en el User-Agent.
_IMG_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "image/avif,image/webp,image/jpeg,image/png,*/*",
}

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RemodelarBot/1.0; +editorial illustrative-image fallback)"}

# Respaldo genérico por categoría editorial (pipeline/editor.py las define),
# sólo para cuando la `image_search_query` puntual del editor no encontró
# nada. Openverse indexa mayormente metadata en inglés.
_CATEGORY_QUERY = {
    "Remodelación": "apartment renovation interior",
    "Materiales": "building material texture architecture",
    "Tendencias": "modern interior design",
    "Interiorismo residencial": "residential interior design",
    "Interiorismo comercial": "retail store interior design",
    "Iluminación": "interior lighting design",
}
_DEFAULT_QUERY = "interior architecture design"


def _ficha(item: dict) -> Optional[dict]:
    url = item.get("url")
    if not url:
        return None
    creator = item.get("creator") or item.get("source") or "autor desconocido"
    license_name = (item.get("license") or "").upper()
    license_version = item.get("license_version", "")
    license_str = f"CC {license_name} {license_version}".strip() if license_name else "licencia abierta"
    return {
        "url": url,
        "thumb": item.get("thumbnail") or "",
        "titulo": item.get("title") or "",
        "credit": f"{creator} - {license_str}",
        "license": license_str,
        "source_url": item.get("foreign_landing_url") or item.get("license_url") or "",
    }


def _query_openverse(query: str, timeout: float, cuantas: int = 1) -> list[dict]:
    params = {
        "q": query,
        "license_type": "commercial,modification",
        "page_size": max(cuantas, 6),
        "mature": "false",
    }
    try:
        resp = requests.get(_API_URL, params=params, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except Exception as exc:  # noqa: BLE001 - es un plus, nunca debe tumbar el pipeline
        log.warning("Busqueda de imagen ilustrativa fallo para '%s': %s", query, exc)
        return []

    salida = []
    for item in results:
        ficha = _ficha(item)
        if ficha:
            salida.append(ficha)
        if len(salida) >= cuantas:
            break
    return salida


def candidatas(category: str, search_hint: str = "", cuantas: int = 6,
               timeout: float = 8.0) -> list[dict]:
    """Varias fotos con licencia para que alguien -o algo que vea- elija.

    Devolver solo la primera fue el error: Openverse ordena por relevancia
    de texto, y el texto de una foto abstracta puede decir "tile pattern"
    sin que la foto tenga nada que ver con un piso.
    """
    intentos = [q for q in (search_hint, _CATEGORY_QUERY.get(category, _DEFAULT_QUERY)) if q]
    vistos, salida = set(), []
    for query in dict.fromkeys(intentos):
        for c in _query_openverse(query, timeout, cuantas):
            if c["url"] in vistos:
                continue
            vistos.add(c["url"])
            salida.append(c)
        if len(salida) >= cuantas:
            break
    return salida[:cuantas]


def search_illustrative_image(category: str, search_hint: str = "", timeout: float = 8.0) -> Optional[dict]:
    """Busca una foto de banco libre coherente con la nota.

    `search_hint` (la image_search_query específica que manda el editor) va
    primero, porque es lo que hace que la foto sea del mismo tipo de
    espacio/material que la nota, no una genérica por categoría. El mapeo
    por categoría es sólo el segundo intento si esa búsqueda no dio nada.

    Devuelve un dict {url, credit, license, source_url} o None si no
    encontró nada o falló la búsqueda (nunca debe tumbar el pipeline).
    """
    tried = []
    if search_hint:
        tried.append(search_hint)
    fallback = _CATEGORY_QUERY.get(category, _DEFAULT_QUERY)
    if fallback not in tried:
        tried.append(fallback)

    for query in tried:
        encontradas = _query_openverse(query, timeout)
        if encontradas:
            return encontradas[0]

    log.info("Sin resultados de imagen ilustrativa (intentos: %s)", tried)
    return None


def alojar(url: str, slug: str, respaldo: str = "") -> str:
    """Baja la foto con licencia y la guarda aqui, en JPEG y al ancho del
    sitio. Enlazarla dejaria la portada a merced de un servidor ajeno, y le
    cargaria a el nuestro trafico.

    `respaldo` es la miniatura del proxy de Openverse, que se usa cuando el
    proveedor no entrega el original (Flickr bloquea por User-Agent). Sale
    mas pequena, pero una foto algo blanda es mejor que ninguna.
    """
    import io

    from PIL import Image

    destino_dir = pathlib.Path(__file__).resolve().parent.parent / "sitegen" / "static" / "libres"
    for intento in [u for u in (url, respaldo) if u]:
        try:
            resp = requests.get(intento, timeout=40, headers=_IMG_HEADERS)
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
        except Exception as exc:  # noqa: BLE001 - se intenta el respaldo
            log.warning("No se pudo bajar %s: %s", intento[:70], exc)
    return ""


def miniatura(url: str, lado: int = 512, timeout: float = 25.0) -> bytes | None:
    """Version pequena en JPEG, para mandarla a revisar.

    Se achica antes de mandarla porque son seis candidatas por nota: a
    tamano completo serian decenas de megas por articulo, todos los dias.
    Se le pasa la miniatura del proxy de Openverse, no el original: el
    proveedor suele bloquear la descarga directa.
    """
    import io

    from PIL import Image

    try:
        resp = requests.get(url, timeout=timeout, headers=_IMG_HEADERS)
        resp.raise_for_status()
        im = Image.open(io.BytesIO(resp.content))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.thumbnail((lado, lado))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=75)
        return buf.getvalue()
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo bajar la miniatura de %s: %s", url[:60], exc)
        return None

