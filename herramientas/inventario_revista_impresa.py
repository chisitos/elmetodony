# -*- coding: utf-8 -*-
"""Inventario del archivo de la revista impresa Remodelar No. 0.

Lista cada sección con su titular, autor, cantidad de fotos y de qué
fotógrafo son — los nombres están en los propios nombres de carpeta.
"""
import io
import pathlib
import re
import sys
import unicodedata
import zipfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = pathlib.Path(r"C:\Users\jemho\Downloads\Revista remodelar\Revista remodelar\material\revista 0")
SEP = re.compile(r"[\\/]")
POR = re.compile(r"[Ff]otos?\s+(?:por|de)\s+(.+)")


def normalizar(s: str) -> str:
    # macOS guarda los nombres en NFD: 'Edicio´n' en vez de 'Edición'.
    return unicodedata.normalize("NFC", s)


def texto_docx(ruta: pathlib.Path) -> list[str]:
    """Lee un .docx sin dependencias: es un zip con XML adentro."""
    with zipfile.ZipFile(ruta) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    plano = re.sub(r"<[^>]+>", "", xml)
    return [l.strip() for l in plano.split("\n") if l.strip()]


def fotografo(ruta: pathlib.Path) -> str | None:
    """El crédito viene en el nombre de la carpeta: 'Fotos por Pinyol'."""
    for parte in SEP.split(str(ruta)):
        m = POR.match(normalizar(parte))
        if m:
            return m.group(1).strip()
    return None


filas = []
for d in sorted(BASE.iterdir()):
    if not d.is_dir():
        continue
    finales = [f for f in d.rglob("*")
               if "final" in str(f).lower() and f.suffix.lower() == ".docx"
               and not f.name.startswith("._")]
    if not finales:
        continue
    lineas = texto_docx(finales[0])
    titular = normalizar(lineas[0])
    bajada = normalizar(lineas[1]) if len(lineas) > 1 else ""
    autor = next((normalizar(l) for l in lineas[:8] if l.lower().startswith("por ")), "")
    fotos = [f for f in d.rglob("*")
             if f.suffix.lower() in (".jpg", ".jpeg") and not f.name.startswith("._")]
    creditos = sorted({c for f in fotos if (c := fotografo(f))})
    filas.append({
        "carpeta": normalizar(d.name),
        "titular": titular,
        "bajada": bajada,
        "autor": autor,
        "palabras": sum(len(l.split()) for l in lineas),
        "fotos": len(fotos),
        "creditos": creditos,
    })

for f in filas:
    print(f"{f['carpeta'][:32]:<34} {f['palabras']:>5}p {f['fotos']:>4}f  "
          f"{f['autor'][:20]:<22} {', '.join(f['creditos'])[:28]}")
    print(f"    {f['titular'][:95]}")

print(f"\n{len(filas)} secciones terminadas")
print(f"con autor firmado: {sum(1 for f in filas if f['autor'])}")
print(f"con fotos:         {sum(1 for f in filas if f['fotos'])}")
print(f"con fotógrafo identificado: {sum(1 for f in filas if f['creditos'])}")
