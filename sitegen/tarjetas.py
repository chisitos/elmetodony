# -*- coding: utf-8 -*-
"""Genera las imágenes para compartir cada nota.

Dos piezas por nota:

- `compartir.jpg` (1200×630) — la previsualización del enlace, la que sale
  en WhatsApp o al pegar la URL en cualquier parte.
- `ig.jpg` (1080×1350) — la publicación de Instagram, en 4:5, que es el
  formato que más alto ocupa en el feed sin que IG lo recorte.
- `pin.jpg` (1000×1500) — Pinterest, en 2:3, que es su proporción nativa.
  A diferencia de Instagram, Pinterest sí conserva el enlace, así que cada
  pin devuelve tráfico al sitio.

SOLO para material propio. Componer la foto de un medio ajeno dentro de una
tarjeta de marca sería alojarla y además alterarla, que es justo lo que el
sitio no hace (ver README, "Imágenes y derechos de autor"). Las notas
curadas reciben una tarjeta tipográfica, sin foto.
"""
from __future__ import annotations

import pathlib
import textwrap

from PIL import Image, ImageDraw, ImageFont

RAIZ = pathlib.Path(__file__).resolve().parent.parent
STATIC = RAIZ / "sitegen" / "static"
FUENTES = STATIC / "fuentes"

TINTA = (10, 10, 10)
PAPEL = (255, 255, 255)
VINO = (0x9C, 0x22, 0x27)

# Los tonos planos de la marca, para la banda de categoría de las tarjetas
# sin foto. Llevan texto negro encima, que es como contrastan.
PLANOS = [(0xE0, 0x84, 0x96), (0xC9, 0x64, 0xAD), (0xED, 0x87, 0x31),
          (0x60, 0xB5, 0xAF), (0xDD, 0xE6, 0x73)]


def _fuente(nombre: str, px: int):
    """Carga una fuente del sitio; si falta, la de PIL, que al menos no
    rompe la generación."""
    ruta = FUENTES / nombre
    if ruta.exists():
        return ImageFont.truetype(str(ruta), px)
    for alt in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(alt, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _ajustar(texto: str, fuente, dib, ancho_max: int) -> list[str]:
    """Parte el titular en líneas que quepan en el ancho dado."""
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        prueba = f"{actual} {p}".strip()
        if dib.textlength(prueba, font=fuente) <= ancho_max:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def _fondo(ancho: int, alto: int, foto: pathlib.Path | None, indice: int) -> Image.Image:
    if foto and foto.exists():
        im = Image.open(foto).convert("RGB")
        # Recorte centrado al formato pedido
        escala = max(ancho / im.width, alto / im.height)
        im = im.resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)
        izq = (im.width - ancho) // 2
        arr = (im.height - alto) // 2
        return im.crop((izq, arr, izq + ancho, arr + alto))
    base = Image.new("RGB", (ancho, alto), PAPEL)
    d = ImageDraw.Draw(base)
    # Trama de plano de obra, el recurso gráfico de la casa
    for x in range(-alto, ancho, 22):
        d.line([(x, alto), (x + alto, 0)], fill=(0xE0, 0xE0, 0xE0), width=2)
    d.rectangle([0, alto - 260, ancho, alto], fill=PLANOS[indice % len(PLANOS)])
    return base


def _componer(ancho: int, alto: int, titular: str, categoria: str,
              firma: str, foto: pathlib.Path | None, indice: int) -> Image.Image:
    im = _fondo(ancho, alto, foto, indice)
    d = ImageDraw.Draw(im, "RGBA")
    margen = round(ancho * 0.075)

    if foto and foto.exists():
        # Velo de abajo hacia arriba: sin él, un titular blanco sobre una
        # foto clara no se lee.
        velo = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
        vd = ImageDraw.Draw(velo)
        alto_velo = round(alto * 0.72)
        for i in range(alto_velo):
            op = int(242 * (i / alto_velo) ** 1.35)
            vd.line([(0, alto - alto_velo + i), (ancho, alto - alto_velo + i)], fill=(8, 8, 8, op))
        im = Image.alpha_composite(im.convert("RGBA"), velo).convert("RGB")
        d = ImageDraw.Draw(im, "RGBA")
        color_texto = PAPEL
    else:
        color_texto = TINTA

    f_tit = _fuente("titular.ttf", round(ancho * 0.072))
    f_pie = _fuente("mono.ttf", round(ancho * 0.026))

    lineas = _ajustar(titular, f_tit, d, ancho - margen * 2)[:4]
    alto_linea = round(ancho * 0.082)
    y = alto - margen - round(ancho * 0.10) - len(lineas) * alto_linea

    # Rótulo de categoría
    if categoria:
        cat = categoria.upper()
        an = d.textlength(cat, font=f_pie)
        d.rectangle([margen, y - round(ancho*0.065), margen + an + 26, y - round(ancho*0.022)], fill=VINO)
        d.text((margen + 13, y - round(ancho*0.058)), cat, font=f_pie, fill=PAPEL)

    for l in lineas:
        d.text((margen, y), l, font=f_tit, fill=color_texto)
        y += alto_linea

    if firma:
        d.text((margen, alto - margen - round(ancho*0.035)), firma.upper(), font=f_pie,
               fill=color_texto if foto else (0x6B, 0x6B, 0x6B))

    # Marca
    logo = STATIC / "marca" / ("logo-blanco.png" if foto else "logo.png")
    if logo.exists():
        lg = Image.open(logo).convert("RGBA")
        an = round(ancho * 0.26)
        lg = lg.resize((an, round(lg.height * an / lg.width)), Image.LANCZOS)
        im.paste(lg, (ancho - margen - lg.width, alto - margen - lg.height), lg)
    return im


def generar(articulo: dict, indice: int) -> dict[str, str]:
    """Devuelve {'compartir': ruta, 'pin': ruta} relativas al sitio.

    Solo las dos que el sitio usa: la previsualizacion del enlace y la de
    Pinterest. Habia una tercera, 4:5, para bajarla y subirla a mano a
    Instagram; se quito el boton, y generar un archivo que nadie abre solo
    engorda el despliegue.
    """
    salida = STATIC / "compartir"
    salida.mkdir(parents=True, exist_ok=True)

    foto = None
    if articulo.get("es_propio") and articulo.get("image_url"):
        url = articulo["image_url"].split("?")[0]
        cand = STATIC / url[len("static/"):] if url.startswith("static/") else None
        if cand and cand.exists():
            foto = cand

    slug = articulo["slug"]
    firma = articulo.get("autor") or articulo.get("source_name", "")
    rutas = {}
    for clave, (an, al) in {"compartir": (1200, 630),
                            "pin": (1000, 1500)}.items():
        im = _componer(an, al, articulo["headline"], articulo.get("category", ""), firma, foto, indice)
        nombre = f"{slug}-{clave}.jpg"
        im.save(salida / nombre, "JPEG", quality=88, optimize=True, progressive=True)
        rutas[clave] = f"static/compartir/{nombre}"
    return rutas
