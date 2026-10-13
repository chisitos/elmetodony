# -*- coding: utf-8 -*-
"""Hoja de contacto de las fotos de una sección del archivo impreso.

Sirve para elegir mirando, en vez de confiar en el tamaño del archivo —
que fue el error de la primera importación: la foto más pesada de la
sección de lavamanos resultó ser una sala.
"""
import base64
import io
import pathlib
import sys

from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ARCHIVO = pathlib.Path(r"C:\Users\jemho\Downloads\Revista remodelar\Revista remodelar\material\revista 0")
SALIDA = pathlib.Path(r"C:\Users\jemho\AppData\Local\Temp\claude\c--Users-jemho-OneDrive-Desktop-KargaCol\1f3cb5ce-f478-4c21-bafe-20caa6584af9\scratchpad")

SECCIONES = sys.argv[1:] or ["15_", "13_", "17_", "8_"]
MAX_POR_SECCION = 12


def carpeta(prefijo: str) -> pathlib.Path | None:
    for d in sorted(ARCHIVO.iterdir()):
        if d.is_dir() and d.name.startswith(prefijo):
            return d
    return None


def miniatura(p: pathlib.Path, lado: int = 230) -> str:
    im = Image.open(p)
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    im.thumbnail((lado, lado), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70)
    return base64.b64encode(buf.getvalue()).decode()


celdas = []
for pref in SECCIONES:
    d = carpeta(pref)
    if not d:
        print(f"  sin carpeta {pref}")
        continue
    fotos = sorted((f for f in d.rglob("*")
                    if f.suffix.lower() in (".jpg", ".jpeg") and not f.name.startswith("._")),
                   key=lambda f: f.stat().st_size, reverse=True)[:MAX_POR_SECCION]
    celdas.append(f'<h2>{pref} — {len(fotos)} de las más grandes</h2><div class="g">')
    for f in fotos:
        im = Image.open(f)
        forma = "apaisada" if im.width > im.height else "vertical"
        celdas.append(
            f'<figure><img src="data:image/jpeg;base64,{miniatura(f)}">'
            f'<figcaption>{f.name[:30]}<br>{im.width}×{im.height} {forma}</figcaption></figure>')
        print(f"  {pref} {f.name[:42]:<44} {im.width}x{im.height} {forma}")
    celdas.append("</div>")

html = ("<!doctype html><meta charset=utf-8><style>"
        "body{font:11px monospace;margin:0;padding:8px}"
        "h2{font:700 13px monospace;margin:14px 0 6px}"
        ".g{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}"
        "figure{margin:0}img{width:100%;display:block}"
        "figcaption{padding:3px 0;color:#444}</style>" + "".join(celdas))
SALIDA.mkdir(parents=True, exist_ok=True)
(SALIDA / "contacto.html").write_text(html, encoding="utf-8")
print(f"\nhoja en {SALIDA / 'contacto.html'}")
