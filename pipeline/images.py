"""Extracción de imagen destacada para cada candidato.

Remodelar es una publicación visual, pero no aloja ni redistribuye fotos
ajenas: cada nota referencia (hotlink) la imagen desde el servidor del medio
original, con crédito y link visible — nunca se descarga ni se sirve desde
acá. Dos niveles, con riesgo de derechos muy distinto:

1. `from_rss_entry` — el thumbnail que el propio feed publica para
   sindicación (media:content, media:thumbnail, enclosure, o el primer
   <img> del post). Es el nivel seguro: un archivo que el medio ya preparó
   y ofrece específicamente para que un lector de feeds lo muestre. Es lo
   único que usa `sources_rss.py`.
2. `fetch_og_image` — meta og:image/twitter:image de la página del
   artículo (fetch liviano de la cabecera HTML, no scrapea el cuerpo). Es
   un nivel de riesgo más alto: normalmente es la foto grande de portada
   del artículo, pensada para compartir en redes, no un thumbnail de
   sindicación. Por eso `sources_rss.py` NO la usa como fallback — sólo la
   usa `sources_web.py`, donde es la única imagen posible.

Si no se encuentra nada, el candidato queda sin imagen y el sitio lo
resuelve con una placa de respaldo prolija (no un ícono de imagen rota).
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import requests

log = logging.getLogger("remodelar.images")

_IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_OG_IMAGE_RE_REV = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']',
    re.IGNORECASE,
)
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RemodelarBot/1.0; +editorial preview fetch)"}


def from_rss_entry(entry) -> Optional[str]:
    """Busca una imagen ya declarada en el propio item del feed."""
    media_content = getattr(entry, "media_content", None)
    if media_content:
        url = media_content[0].get("url")
        if url:
            return url

    media_thumb = getattr(entry, "media_thumbnail", None)
    if media_thumb:
        url = media_thumb[0].get("url")
        if url:
            return url

    for link in getattr(entry, "links", []) or []:
        if link.get("rel") == "enclosure" and str(link.get("type", "")).split("/")[0] in ("", "image"):
            href = link.get("href")
            if href:
                return href

    content = ""
    if getattr(entry, "content", None):
        content = entry.content[0].get("value", "")
    match = _IMG_RE.search(content)
    if match:
        return match.group(1)

    match = _IMG_RE.search(getattr(entry, "summary", "") or "")
    if match:
        return match.group(1)

    return None


def fetch_og_image(url: str, timeout: float = 6.0) -> Optional[str]:
    """Fallback: trae sólo el arranque del HTML y busca og:image/twitter:image."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout, stream=True)
        resp.raise_for_status()
        chunk = next(resp.iter_content(chunk_size=131072), b"")
        resp.close()
    except Exception as exc:  # noqa: BLE001 — la imagen es un plus, nunca debe tumbar el pipeline
        log.debug("No se pudo obtener og:image de %s: %s", url, exc)
        return None

    text = chunk.decode("utf-8", errors="ignore")
    match = _OG_IMAGE_RE.search(text) or _OG_IMAGE_RE_REV.search(text)
    return match.group(1) if match else None
