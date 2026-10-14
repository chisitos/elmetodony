# -*- coding: utf-8 -*-
"""Busca en Wikimedia Commons una foto que SI se pueda republicar.

Por que existe: las notas curadas traian la foto del medio original por
enlace directo. Eso no es republicar con permiso, es usar su servidor y su
imagen sin licencia. Commons es la unica fuente que verificamos que si
permite republicar y traducir, siempre que se acredite.

Que se acepta: dominio publico, CC0, CC BY y CC BY-SA. Nada de ND (prohibe
modificar, y recortar para una tarjeta es modificar) ni NC (el sitio lleva
publicidad de la feria, asi que no es uso no comercial).

Que NO resuelve: para una nota sobre UN proyecto concreto -el apartamento
de tal estudio en Roma- no hay foto libre de ese proyecto. Una foto
generica de otro lugar puesta ahi le miente al lector. Para esas notas la
salida honesta es texto propio y un enlace a la fuente para ver las fotos,
no una foto parecida.
"""
from __future__ import annotations

import io
import json
import pathlib
import sys
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API = "https://commons.wikimedia.org/w/api.php"
AGENTE = "FeriaRemodelar/1.0 (https://feriaremodelar.com; contacto por el sitio)"

# Licencias que permiten republicar y recortar, acreditando.
PERMITIDAS = ("cc0", "public domain", "pd", "cc by 1.0", "cc by 2.0", "cc by 2.5",
              "cc by 3.0", "cc by 4.0", "cc by-sa 1.0", "cc by-sa 2.0",
              "cc by-sa 2.5", "cc by-sa 3.0", "cc by-sa 4.0")
VETADAS = ("nd", "nc", "fair use", "non-free")

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "sitegen" / "static" / "libres"
SALIDA = pathlib.Path(__file__).resolve().parent.parent / "scratch_artifacts"


def _pedir(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _limpio(html: str) -> str:
    import re
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def _aceptable(lic: str) -> bool:
    l = (lic or "").lower()
    if any(v in l for v in VETADAS):
        return False
    return any(p in l for p in PERMITIDAS)


def buscar(consulta: str, limite: int = 8) -> list[dict]:
    """Candidatas para una consulta, ya filtradas por licencia."""
    datos = _pedir({
        "action": "query",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {consulta}",
        "gsrnamespace": "6",
        "gsrlimit": str(limite * 3),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": "1400",
    })
    salida = []
    for pag in (datos.get("query", {}).get("pages") or {}).values():
        info = (pag.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = _limpio(meta.get("LicenseShortName", {}).get("value", ""))
        if not _aceptable(lic) or info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if (info.get("width") or 0) < 1200:
            continue
        salida.append({
            "titulo": pag["title"],
            "url": info.get("thumburl") or info.get("url"),
            "ancho": info.get("width"),
            "licencia": lic,
            "autor": _limpio(meta.get("Artist", {}).get("value", "")) or "autor no indicado",
            "pagina": info.get("descriptionurl", ""),
        })
        if len(salida) >= limite:
            break
    return salida


def descargar(cand: dict, slug: str) -> str:
    """Guarda la foto en el sitio, en JPEG y al ancho del sitio.

    Se aloja, no se enlaza: enlazar al servidor ajeno lo hace pagar el
    trafico, deja la pagina a merced de que la borren, y es lo que veniamos
    haciendo mal con las notas curadas.
    """
    from PIL import Image

    DESTINO.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(cand["url"], headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(req, timeout=60) as r:
        im = Image.open(io.BytesIO(r.read()))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    if im.width > 1400:
        im.thumbnail((1400, 1400 * 3), Image.LANCZOS)
    destino = DESTINO / (slug + ".jpg")
    im.save(destino, "JPEG", quality=82, optimize=True, progressive=True)
    return "static/libres/" + destino.name


# --------------------------------------------------------------------------
# Elegir mirando, no a ciegas.
#
# La busqueda devuelve cosas buenas y cosas absurdas en la misma lista: para
# "paneles acusticos" trajo un muro antirruido de autopista, y para
# "lavamanos" uno de un submarino. Tomar la primera repetiria el error de la
# importacion del archivo, cuando la nota de lavamanos abrio con una sala.
# Asi que se arma una hoja de contacto y la foto la elige una persona.

def hoja(cands: list[dict], consulta: str) -> pathlib.Path:
    from PIL import Image, ImageDraw
    lado, cols = 300, 4
    filas = (len(cands) + cols - 1) // cols
    lamina = Image.new("RGB", (cols * lado, filas * (lado + 46) + 34), "white")
    dib = ImageDraw.Draw(lamina)
    dib.text((10, 10), consulta + "  -  " + str(len(cands)) + " candidatas", fill="black")

    for i, c in enumerate(cands):
        x, y = (i % cols) * lado, 34 + (i // cols) * (lado + 46)
        try:
            req = urllib.request.Request(c["url"], headers={"User-Agent": AGENTE})
            with urllib.request.urlopen(req, timeout=30) as r:
                im = Image.open(io.BytesIO(r.read())).convert("RGB")
            im.thumbnail((lado - 10, lado - 10))
            lamina.paste(im, (x + 5, y + 5))
        except Exception as exc:
            dib.text((x + 8, y + 8), ("no cargo: " + str(exc))[:40], fill="red")
        dib.text((x + 6, y + lado + 2), "[" + str(i) + "] " + c["licencia"], fill="black")
        dib.text((x + 6, y + lado + 16), c["titulo"].replace("File:", "")[:46], fill="#555")
        dib.text((x + 6, y + lado + 30), c["autor"][:46], fill="#555")

    destino = SALIDA / ("libres-" + consulta.replace(" ", "-")[:40] + ".jpg")
    lamina.save(destino, "JPEG", quality=84)
    return destino


def aplicar(slug: str, cand: dict) -> None:
    """Aloja la foto y le escribe a la nota su credito y su licencia.

    El credito no es decorativo: CC BY y CC BY-SA obligan a nombrar al autor
    y a enlazar la licencia. Sin eso, el permiso no aplica.
    """
    notas = sorted((RAIZ / "data" / "articles").glob("*" + slug + "*.json"))
    if not notas:
        raise SystemExit("no hay nota que coincida con " + slug)
    ruta = notas[0]
    nota = json.loads(ruta.read_text(encoding="utf-8"))
    nota["image_url"] = descargar(cand, nota["slug"])
    nota["image_credit"] = cand["autor"] + " - " + cand["licencia"] + " - Wikimedia Commons"
    nota["image_license"] = cand["licencia"]
    nota["image_source_url"] = cand["pagina"]
    # La foto es del tema, no del proyecto del que habla la nota.
    nota["image_is_illustrative"] = True
    ruta.write_text(json.dumps(nota, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    print(ruta.name + ": " + nota["image_url"] + "  (" + nota["image_credit"] + ")")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--aplicar":
        # --aplicar <slug> <indice> <consulta...>
        slug, indice, consulta = args[1], int(args[2]), " ".join(args[3:])
        aplicar(slug, buscar(consulta)[indice])
    else:
        consulta = " ".join(args) or "bathroom sink interior"
        cands = buscar(consulta)
        for i, c in enumerate(cands):
            print(f"[{i}] {c['licencia']:<14} {c['ancho']:>5}px  "
                  f"{c['autor'][:26]:<28} {c['titulo'][:58]}")
        if cands:
            print()
            print("hoja de contacto:", hoja(cands, consulta))
