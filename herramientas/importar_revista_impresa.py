# -*- coding: utf-8 -*-
"""Importa artículos del archivo de la Revista Remodelar No. 0 impresa.

Convierte un .docx corregido en una nota del sitio y copia su mejor foto a
`sitegen/static/revista/`. A diferencia de lo que trae el pipeline de RSS,
esto es material PROPIO: la foto se aloja (no se enlaza) y el crédito lleva
el nombre de quien escribió y de quien fotografió.

Uso:
    python herramientas/importar_revista_impresa.py
"""
from __future__ import annotations

import io
import json
import pathlib
import re
import sys
import unicodedata
import zipfile
from datetime import datetime, timezone

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ARCHIVO = pathlib.Path(r"C:\Users\jemho\Downloads\Revista remodelar\Revista remodelar\material\revista 0")
DESTINO_FOTOS = RAIZ / "sitegen" / "static" / "revista"
DESTINO_NOTAS = RAIZ / "data" / "articles"

# Qué se publica en esta edición y cómo se acredita. El orden es el de la
# portada: primero lo que conversa con las Rutas.
SELECCION = [
    {
        "carpeta": "8_Remodelar Paso a Paso",
        "slug": "paso-a-paso-para-una-transformacion",
        "categoria": "Cómo remodelar",
        "tags": ["remodelación", "planeación", "presupuesto", "arquitecto", "obra"],
        "fotografo": "",
        # Esta sección no trae foto. Se toma una de obra en proceso: es lo que
        # el texto describe, paso por paso.
        "foto_de": "27_Proyecto_Bathyard Home",
        "foto_archivo": "IMG_8967.JPG",
    },
    {
        "carpeta": "15_¿Cuanto Cuesta_",
        "slug": "lavamanos-eleccion-a-la-medida",
        "categoria": "Baños",
        "tags": ["lavamanos", "baños", "precios", "materiales", "grifería"],
        "fotografo": "",
        # Las fotos de la sección 15 son todas de cocinas (DOSDE, SeisAsiete,
        # STOSA): ninguna de baño. Se toma la del baño de Bathyard.
        "foto_de": "27_Proyecto_Bathyard Home",
        "foto_archivo": "00042_PIC_15.jpg",
    },
    {
        "carpeta": "13_Consejos para Remodelar con Vegetación",
        "slug": "jardines-de-interior-sin-misterios",
        "categoria": "Jardines",
        "tags": ["jardines", "plantas", "interior", "luz natural", "riego"],
        "fotografo": "",
        # Apaisada: las verticales de esta sección son retratos y el recorte
        # 16:9 les corta la cara.
        "foto_archivo": "FNS_0073.jpg",
    },
    {
        "carpeta": "17_La Iluminacion también es diseño",
        "slug": "disenar-con-luz",
        "categoria": "Iluminación",
        "tags": ["iluminación", "luz", "diseño interior", "temperatura de color"],
        "fotografo": "",
        # Interior con luz de color: el tema del artículo, no el retrato del
        # arquitecto que las verticales de esta carpeta repiten.
        "foto_archivo": "FNS_2235.jpg",
    },
    {
        "carpeta": "9_Proyecto_Veronica Ochoa",
        "slug": "el-apartamento-que-se-hizo-casa",
        "categoria": "Proyecto",
        "tags": ["remodelación", "apartamento", "medellín", "interiorismo"],
        "fotografo": "",
        "foto_archivo": "FNS_1986.jpg",
    },
    {
        "carpeta": "11_Proyecto_Casa Trujillo",
        "slug": "la-casa-trujillo-vuelve-a-vivir",
        "categoria": "Patrimonio",
        "tags": ["patrimonio", "bogotá", "restauración", "vivienda", "bauhaus"],
        "fotografo": "Santiago Pinyol",
    },
]

ANCHOS = {"": 1400, "-sm": 400}


def nfc(s: str) -> str:
    """macOS guarda los nombres en NFD; sin esto no coinciden las rutas."""
    return unicodedata.normalize("NFC", s)


def carpeta_de(nombre: str) -> pathlib.Path | None:
    """Empareja por el número de sección ('15_', '9_'...). Comparar el
    nombre completo falla: macOS guarda los acentos descompuestos (NFD) y
    'Vegetación' no coincide consigo mismo entre sistemas."""
    prefijo = nombre.split("_")[0] + "_"
    for d in sorted(ARCHIVO.iterdir()):
        if d.is_dir() and d.name.startswith(prefijo):
            return d
    return None


def lineas_docx(ruta: pathlib.Path) -> list[str]:
    """Un .docx es un zip con XML; se lee sin dependencias."""
    with zipfile.ZipFile(ruta) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    plano = re.sub(r"<[^>]+>", "", xml)
    return [nfc(l.strip()) for l in plano.split("\n") if l.strip()]


def doc_final(d: pathlib.Path) -> pathlib.Path | None:
    cands = [f for f in d.rglob("*")
             if "final" in str(f).lower() and f.suffix.lower() == ".docx"
             and not f.name.startswith("._")]
    return cands[0] if cands else None


_USADAS: set[str] = set()


def foto_por_nombre(d: pathlib.Path, nombre: str) -> pathlib.Path | None:
    for f in d.rglob("*"):
        if f.name == nombre and not f.name.startswith("._"):
            return f
    return None


def mejor_foto(d: pathlib.Path) -> pathlib.Path | None:
    """La más pesada suele ser la de mayor resolución, y es la de apertura.
    Se descartan las ya usadas para que dos notas no abran con la misma."""
    fotos = sorted((f for f in d.rglob("*")
                    if f.suffix.lower() in (".jpg", ".jpeg") and not f.name.startswith("._")),
                   key=lambda f: f.stat().st_size, reverse=True)
    for f in fotos:
        if f.name not in _USADAS:
            _USADAS.add(f.name)
            return f
    return fotos[0] if fotos else None


def procesar_foto(origen: pathlib.Path, slug: str) -> str:
    """Reduce y guarda en dos tamaños. Devuelve la ruta relativa al sitio."""
    DESTINO_FOTOS.mkdir(parents=True, exist_ok=True)
    im = Image.open(origen)
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    for sufijo, ancho in ANCHOS.items():
        copia = im.copy()
        if copia.width > ancho:
            copia.thumbnail((ancho, ancho * 3), Image.LANCZOS)
        copia.save(DESTINO_FOTOS / f"{slug}{sufijo}.jpg", "JPEG",
                   quality=82, optimize=True, progressive=True)
    return f"static/revista/{slug}.jpg"


def partir(lineas: list[str]) -> tuple[str, str, str, list[str]]:
    """Separa titular, bajada, firma y cuerpo."""
    titular = lineas[0]
    autor, resto = "", []
    bajada = ""
    for i, l in enumerate(lineas[1:], 1):
        if l.lower().startswith("por ") and len(l) < 60 and not autor:
            autor = l[4:].strip()
            continue
        if not bajada and len(l) > 40:
            bajada = l
            continue
        resto.append(l)
    return titular, bajada, autor, resto


def main() -> int:
    DESTINO_NOTAS.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now(timezone.utc)
    hechas = 0

    for i, item in enumerate(SELECCION):
        d = carpeta_de(item["carpeta"])
        if not d:
            print(f"  NO ENCONTRADA  {item['carpeta']}")
            continue
        doc = doc_final(d)
        if not doc:
            print(f"  SIN DOC FINAL  {item['carpeta']}")
            continue

        titular, bajada, autor, cuerpo = partir(lineas_docx(doc))
        if not cuerpo:
            print(f"  SIN CUERPO     {item['carpeta']}")
            continue

        # La foto puede venir de otra sección cuando la propia no tiene.
        origen_foto = carpeta_de(item.get("foto_de") or item["carpeta"])
        f = None
        if origen_foto:
            if item.get("foto_archivo"):
                f = foto_por_nombre(origen_foto, item["foto_archivo"])
                if not f:
                    print(f"  OJO: no está {item['foto_archivo']} en {item['carpeta']}")
            f = f or mejor_foto(origen_foto)
        img = procesar_foto(f, item["slug"]) if f else None

        credito = item.get("fotografo") or "Revista Remodelar"
        # Si la foto viene de otra sección, no documenta ESTE artículo: es
        # del archivo propio, pero ilustra. El sitio ya sabe decirlo.
        prestada = bool(item.get("foto_de")) and item["foto_de"] != item["carpeta"]

        nota = {
            "slug": f"{ahora:%Y-%m-%d}-{item['slug']}",
            "headline": titular,
            "dek": bajada or cuerpo[0][:200],
            "body_md": "\n\n".join(cuerpo),
            "pull_quote": max((l for l in cuerpo if 60 < len(l) < 190), key=len, default=""),
            "tags": item["tags"],
            "category": item["categoria"],
            "source_name": "Revista Remodelar",
            "source_url": "",
            "autor": autor,
            "es_propio": True,
            # Se mantiene el orden de la selección: published_at desciende.
            "published_at": ahora.replace(microsecond=0).isoformat().replace("+00:00", f"+00:00"),
            "original_published_at": None,
            "scores": {},
            "weighted_score": 0.0,
            "image_url": img,
            "image_credit": credito,
            "image_is_illustrative": prestada,
            "image_license": "",
            "image_source_url": "",
            "image_search_hint": "",
        }
        # Desfase de un segundo por nota para fijar el orden de portada.
        from datetime import timedelta
        ts = ahora - timedelta(seconds=i)
        nota["published_at"] = ts.replace(microsecond=0).isoformat()

        destino = DESTINO_NOTAS / f"{nota['slug']}.json"
        destino.write_text(json.dumps(nota, ensure_ascii=False, indent=2), encoding="utf-8")
        hechas += 1
        print(f"  OK  {titular[:48]:<50} {len(nota['body_md'].split()):>4} pal."
              f"  {'foto' if img else 'SIN FOTO':<8} {autor or '(sin firma)'}")

    print(f"\n{hechas}/{len(SELECCION)} notas importadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
