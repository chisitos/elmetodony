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

from PIL import Image, ImageDraw

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ORIGEN = pathlib.Path(r"C:\Users\jemho\OneDrive\Desktop\Feria remodelar")
DEST = pathlib.Path(__file__).resolve().parent.parent / "sitegen" / "static"
MARCA = DEST / "marca"


# De que archivo sale el icono. Cambia cuando rota la paleta de la
# edicion; el resto del proceso no se toca.
ICONO_FUENTE = "paleta2.png"

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

    # --- icono: el cuadrado completo, a sangre, sin recortar en circulo ---
    #
    # Tres intentos de recorte circular salieron mal: la R quedaba chica y
    # flotando, con un fondo de colores repetidos que no calzaba limpio con
    # el borde. La salida correcta es la simple: mandar el arte cuadrado tal
    # cual, sin encoger nada. Asi se entregan los iconos de apps -arte
    # cuadrado a sangre completa- y es el propio sistema el que aplica su
    # propio redondeado (iOS) o su mascara (Android) encima.
    ico = ORIGEN / ICONO_FUENTE
    if not ico.exists():
        print(f"\n  OJO: falta {ico.name}; el icono no se regenera")
        return 0

    base = Image.open(ico).convert("RGB")
    lado = min(base.size)
    izq, arr = (base.width - lado) // 2, (base.height - lado) // 2
    base = base.crop((izq, arr, izq + lado, arr + lado))

    for px, nombre in [(512, "icono-512-nuevo.png"), (192, "icono-192-nuevo.png"),
                       (180, "icono-180-nuevo.png")]:
        base.resize((px, px), Image.LANCZOS).save(DEST / nombre, "PNG", optimize=True)
        print(f"  {nombre:<24} {px}x{px}  cuadrado completo")

    # El maskable de Android SI necesita margen: el sistema recorta en
    # circulo o squircle por su cuenta, y sin encoger la R quedaria
    # mutilada en las esquinas, que es justo donde estan el asta y la cola.
    px = 512
    lienzo = Image.new("RGB", (px, px), base.getpixel((4, 4)))
    disp = round(px * 0.72)
    lienzo.paste(base.resize((disp, disp), Image.LANCZOS), ((px - disp) // 2, (px - disp) // 2))
    lienzo.save(DEST / "icono-maskable-512-nuevo.png", "PNG", optimize=True)
    print(f"  {'icono-maskable-512-nuevo.png':<24} {px}x{px}  con margen de seguridad")
    return 0


if __name__ == "__main__":
    sys.exit(main())
