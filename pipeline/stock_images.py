"""Fallback de imagen ilustrativa vía Openverse, para cuando el candidato no
trajo foto propia (ni del RSS ni de la fuente).

Diferencia clave con `pipeline/images.py`: esto NUNCA es una foto del
proyecto/objeto real descrito en la nota — es una foto genérica de banco
libre, elegida por categoría temática. Por eso el sitio la marca siempre
como "imagen ilustrativa" y nunca la mezcla visualmente con una foto real
de la obra (ver `image_is_illustrative` en pipeline/models.py).

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
from typing import Optional

import requests

log = logging.getLogger("remodelar.stock_images")

_API_URL = "https://api.openverse.org/v1/images/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RemodelarBot/1.0; +editorial illustrative-image fallback)"}

# Cada categoría editorial (pipeline/editor.py las define) se traduce a un
# término de búsqueda en inglés — Openverse indexa mayormente metadata en
# inglés, así que buscar en español da resultados pobres.
_CATEGORY_QUERY = {
    "Remodelación": "apartment renovation interior",
    "Materiales": "building material texture architecture",
    "Tendencias": "modern interior design",
    "Interiorismo residencial": "residential interior design",
    "Interiorismo comercial": "retail store interior design",
    "Iluminación": "interior lighting design",
}
_DEFAULT_QUERY = "interior architecture design"


def search_illustrative_image(category: str, timeout: float = 8.0) -> Optional[dict]:
    """Busca una foto de banco libre para ilustrar `category`.

    Devuelve un dict {url, credit, license, source_url} o None si no
    encontró nada o falló la búsqueda (nunca debe tumbar el pipeline).
    """
    query = _CATEGORY_QUERY.get(category, _DEFAULT_QUERY)
    params = {
        "q": query,
        "license_type": "commercial,modification",
        "page_size": 6,
        "mature": "false",
    }
    try:
        resp = requests.get(_API_URL, params=params, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except Exception as exc:  # noqa: BLE001 — es un plus, nunca debe tumbar el pipeline
        log.warning("Búsqueda de imagen ilustrativa falló para '%s': %s", category, exc)
        return None

    for item in results:
        url = item.get("url")
        if not url:
            continue
        creator = item.get("creator") or item.get("source") or "autor desconocido"
        license_name = item.get("license", "").upper()
        license_version = item.get("license_version", "")
        license_str = f"CC {license_name} {license_version}".strip() if license_name else "licencia abierta"
        return {
            "url": url,
            "credit": f"{creator} · {license_str}",
            "license": license_str,
            "source_url": item.get("foreign_landing_url") or item.get("license_url") or "",
        }

    log.info("Sin resultados de imagen ilustrativa para categoría '%s' (query: %s)", category, query)
    return None
