# -*- coding: utf-8 -*-
"""Mete al sitio las fotos de la carpeta de fotos propias.

Por que existe: el motor buscaba la foto de cada nota en un banco de
imagenes libre, y para una revista de interiores eso no da. Para la nota
de porcelanato trajo un patron azul abstracto; con revision visual mejoro,
pero lo mejor que consiguio fue una baldosa de barro, que no es
porcelanato. Los bancos libres no tienen interiores contemporaneos.

Lo que si tenemos son 640 fotos del archivo de la revista y las que se
tomen en las tiendas y en la feria. Esto las deja disponibles para el
motor, con su credito, y el motor las prefiere antes de salir a buscar
afuera.

Creditos: si al lado de la foto hay un .txt con el mismo nombre, su
contenido es el credito. Si no, la foto es del archivo propio. Esto
importa: una foto que una tienda nos presto no es nuestra, y el sitio
tiene que poder decirlo.
"""
from __future__ import annotations

import io
import json
import pathlib
import sys

from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ORIGEN = pathlib.Path(r"C:\Users\jemho\OneDrive\Desktop\Feria remodelar\fotos propias")
RAIZ = pathlib.Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "sitegen" / "static" / "propias"
CATALOGO = RAIZ / "data" / "fotos_propias.json"

EXTS = (".jpg", ".jpeg", ".png", ".webp")
ANCHO = 1400


def creditos_de(foto: pathlib.Path) -> str:
    """El .txt hermano manda; si no hay, es del archivo propio."""
    gemelo = foto.with_suffix(".txt")
    if gemelo.exists():
        texto = gemelo.read_text(encoding="utf-8", errors="replace").strip()
        if texto:
            return " ".join(texto.split())
    return "Archivo Feria Remodelar"


def main() -> int:
    if not ORIGEN.exists():
        print(f"No existe la carpeta:\n  {ORIGEN}")
        return 1

    DESTINO.mkdir(parents=True, exist_ok=True)
    catalogo: list[dict] = []
    saltadas = 0

    for tema_dir in sorted(p for p in ORIGEN.iterdir() if p.is_dir()):
        tema = tema_dir.name
        fotos = sorted(f for f in tema_dir.rglob("*")
                       if f.suffix.lower() in EXTS and not f.name.startswith("._"))
        if not fotos:
            continue

        for i, f in enumerate(fotos, start=1):
            nombre = f"{tema}-{i:02d}.jpg"
            try:
                im = Image.open(f)
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                # Horizontal manda: la foto de apertura es apaisada, y una
                # vertical recortada al centro suele cortar lo importante.
                apaisada = im.width >= im.height
                if im.width > ANCHO:
                    im.thumbnail((ANCHO, ANCHO * 3), Image.LANCZOS)
                im.save(DESTINO / nombre, "JPEG", quality=82,
                        optimize=True, progressive=True)
            except Exception as exc:  # noqa: BLE001
                print(f"  no se pudo leer {f.name}: {exc}")
                saltadas += 1
                continue

            catalogo.append({
                "tema": tema,
                "url": f"static/propias/{nombre}",
                "credito": creditos_de(f),
                "apaisada": apaisada,
                "origen": f.name,
            })

    CATALOGO.parent.mkdir(parents=True, exist_ok=True)
    CATALOGO.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    por_tema: dict[str, int] = {}
    for c in catalogo:
        por_tema[c["tema"]] = por_tema.get(c["tema"], 0) + 1
    print(f"{len(catalogo)} fotos listas en {DESTINO}")
    for t, n in sorted(por_tema.items()):
        print(f"   {n:>4}  {t}")
    if saltadas:
        print(f"   ({saltadas} no se pudieron leer)")
    if not catalogo:
        print("\nLa carpeta esta vacia todavia. Lea el LEAME.txt que esta ahi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
