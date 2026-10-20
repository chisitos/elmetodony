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
ICONO_FUENTE = "icono cuadrante 2.png"

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

    # --- icono: la R de los cuadrantes, recortada en circulo ---
    ico = ORIGEN / ICONO_FUENTE
    if not ico.exists():
        print(f"\n  OJO: falta {ico.name}; el icono no se regenera")
        return 0

    # Sobre blanco antes de pasar a RGB. El archivo trae transparencia en
    # las lineas que separan los cuadrantes: convertir directo a RGB las
    # pinta de NEGRO, y el icono queda cruzado por dos rayas negras.
    crudo = Image.open(ico).convert("RGBA")
    base = Image.new("RGB", crudo.size, "white")
    base.paste(crudo, (0, 0), crudo)

    lado = min(base.size)
    izq, arr = (base.width - lado) // 2, (base.height - lado) // 2
    base = base.crop((izq, arr, izq + lado, arr + lado))

    # Colores de cada cuadrante, tomados adentro de cada uno.
    q = lado // 4
    colores = [base.getpixel((q, q)), base.getpixel((lado - q, q)),
               base.getpixel((q, lado - q)), base.getpixel((lado - q, lado - q))]
    # Grosor de la linea blanca que separa los cuadrantes, en proporcion.
    grosor = max(1, round(lado * 0.009))

    def icono(px: int, encoge: float = 0.0) -> Image.Image:
        """Circulo con los cuatro cuadrantes y la R adentro.

        El dibujo se encoge un poco y el fondo se completa con los mismos
        cuatro colores. Si se dejara la imagen llenando el circulo, el
        recorte le comeria los extremos a la R: la letra ocupa casi todo el
        ancho, y lo que sobra de un cuadrado al inscribirle un circulo son
        justo las esquinas donde esta el asta y la cola.
        """
        fondo = Image.new("RGB", (px, px))
        m = px // 2
        for (x, y), c in zip([(0, 0), (m, 0), (0, m), (m, m)], colores):
            fondo.paste(Image.new("RGB", (m, m), c), (x, y))
        # Las lineas siguen hasta el borde, para que no se corten a medias.
        d = ImageDraw.Draw(fondo)
        g = max(1, round(px * 0.009))
        d.rectangle([m - g // 2, 0, m + g // 2, px], fill="white")
        d.rectangle([0, m - g // 2, px, m + g // 2], fill="white")

        if encoge:
            dentro = round(px * (1 - encoge))
            fondo.paste(base.resize((dentro, dentro), Image.LANCZOS),
                        ((px - dentro) // 2, (px - dentro) // 2))
        else:
            fondo = base.resize((px, px), Image.LANCZOS)

        # Mascara al cuadruple y reducida: dibujarla al tamano final deja
        # el borde dentado, y en 180 px se nota.
        e = 4
        mascara = Image.new("L", (px * e, px * e), 0)
        ImageDraw.Draw(mascara).ellipse((0, 0, px * e - 1, px * e - 1), fill=255)
        mascara = mascara.resize((px, px), Image.LANCZOS)
        salida = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        salida.paste(fondo, (0, 0), mascara)
        return salida

    # 0.14 dentro del circulo deja respirar la R sin que el dibujo se vea
    # perdido en el medio.
    #
    # Estos van CON transparencia: es el circulo flotando, que es como debe
    # verse en la pestana del navegador y en el manifiesto.
    for px, nombre in [(512, "icono-512.png"), (192, "icono-192.png")]:
        icono(px, 0.14).save(DEST / nombre, "PNG", optimize=True)
        print(f"  {nombre:<24} {px}x{px}  circular, transparente")

    def sobre_blanco(im: Image.Image, px: int, encoge: float = 0.0) -> Image.Image:
        """Pega el circulo sobre blanco, sin alfa."""
        lienzo = Image.new("RGB", (px, px), "white")
        if encoge:
            d = round(px * (1 - encoge))
            chico = icono(d, 0.14)
            lienzo.paste(chico.convert("RGB"), ((px - d) // 2, (px - d) // 2),
                         chico.split()[3])
        else:
            lienzo.paste(im.convert("RGB"), (0, 0), im.split()[3])
        return lienzo

    # iOS: Safari NO admite transparencia en el apple-touch-icon y rellena
    # de negro. Por eso este va sobre blanco. El sistema le pone encima su
    # propio redondeado.
    sobre_blanco(icono(180, 0.14), 180).save(DEST / "icono-180.png", "PNG", optimize=True)
    print(f"  {'icono-180.png':<24} 180x180  sobre blanco (iOS no acepta alfa)")

    # Android recorta el maskable por su cuenta en circulo o squircle, asi
    # que la marca va mas adentro y el fondo tiene que ser opaco: lo
    # transparente tambien le sale negro.
    sobre_blanco(None, 512, 0.28).save(DEST / "icono-maskable-512.png", "PNG", optimize=True)
    print(f"  {'icono-maskable-512.png':<24} 512x512  sobre blanco, con margen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
