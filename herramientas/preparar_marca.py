# -*- coding: utf-8 -*-
"""Prepara los archivos de marca para la web.

El PNG que entrega diseño viene con fondo BLANCO opaco. Para la web hace
falta transparencia, pero no sirve derivar el alfa de la luminancia: los
colores de la R son de tono medio, así que quedarían semitransparentes y
el logotipo se ve como una marca de agua.

El método correcto deshace la mezcla con el blanco. Un píxel sobre fondo
blanco vale  p = c·a + 255·(1−a), donde c es el color real y a la
cobertura. Se estima a por la distancia al blanco del canal más oscuro y
se despeja c, que recupera el color a plena saturación.
"""
from __future__ import annotations

import io
import pathlib
import sys

from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ORIGEN = pathlib.Path(r"C:\Users\jemho\OneDrive\Desktop\Feria remodelar")
DEST = pathlib.Path(__file__).resolve().parent.parent / "sitegen" / "static"
MARCA = DEST / "marca"


def quitar_blanco(im: Image.Image, umbral: int = 232) -> Image.Image:
    """Blanco -> transparente, el resto opaco con SU color.

    El logotipo son colores planos sobre blanco. Lo que hay que hacer es
    recortar el fondo, no calcular coberturas: estimar el alfa desde la
    luminancia deja los tonos medios semitransparentes —el logotipo se ve
    como marca de agua— y deshacer la mezcla los oscurece.

    Sólo el borde antialias, entre `umbral` y blanco puro, recibe alfa
    parcial, que es lo que evita el dentado.
    """
    im = im.convert("RGB")
    ancho, alto = im.size
    px = im.load()
    salida = Image.new("RGBA", (ancho, alto))
    sp = salida.load()
    for y in range(alto):
        for x in range(ancho):
            r, g, b = px[x, y]
            claro = min(r, g, b)
            if claro >= 252:
                sp[x, y] = (0, 0, 0, 0)
            elif claro > umbral:
                # banda de antialias
                a = round(255 * (252 - claro) / (252 - umbral))
                sp[x, y] = (r, g, b, a)
            else:
                sp[x, y] = (r, g, b, 255)
    return salida


def main() -> int:
    MARCA.mkdir(parents=True, exist_ok=True)

    # --- logotipo horizontal, para la cabecera ---
    h = Image.open(ORIGEN / "Logo remodelar.png").convert("RGB")
    h = h.crop(h.getbbox() or (0, 0, *h.size))
    ht = quitar_blanco(h)
    for ancho, nombre in [(1200, "logo.png"), (600, "logo-400.png"), (2400, "logo-2x.png")]:
        c = ht.resize((ancho, round(ht.height * ancho / ht.width)), Image.LANCZOS)
        c.save(MARCA / nombre, "PNG", optimize=True)
        print(f"  {nombre:<14} {c.size}")

    # Versión blanca, para fondos oscuros (tarjetas de compartir)
    blanco = Image.new("RGBA", ht.size, (255, 255, 255, 255))
    blanco.putalpha(ht.getchannel("A"))
    blanco.resize((1200, round(ht.height * 1200 / ht.width)), Image.LANCZOS) \
          .save(MARCA / "logo-blanco.png", "PNG", optimize=True)
    print("  logo-blanco.png")

    # --- ícono: la R sobre los cuatro cuadrantes de color ---
    ico = ORIGEN / "icono-cuadrantes.png"
    if not ico.exists():
        print(f"\n  OJO: falta {ico.name}; el ícono no se regenera")
        return 0
    base = Image.open(ico).convert("RGB")
    base = base.crop(base.getbbox() or (0, 0, *base.size))
    for px, nombre, margen in [(512, "icono-512.png", 0.0),
                               (192, "icono-192.png", 0.0),
                               (180, "icono-180.png", 0.0),
                               # Android recorta en círculo: la marca se
                               # encoge y el resto se rellena con su color.
                               (512, "icono-maskable-512.png", 0.18)]:
        if margen:
            lienzo = Image.new("RGB", (px, px), base.getpixel((2, 2)))
            disp = round(px * (1 - margen * 2))
            c = base.resize((disp, disp), Image.LANCZOS)
            lienzo.paste(c, ((px - disp) // 2, (px - disp) // 2))
        else:
            lienzo = base.resize((px, px), Image.LANCZOS)
        lienzo.save(DEST / nombre, "PNG", optimize=True)
        print(f"  {nombre:<24} {px}x{px}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
