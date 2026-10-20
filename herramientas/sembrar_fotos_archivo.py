# -*- coding: utf-8 -*-
"""Siembra el catalogo de fotos propias con una seleccion del archivo.

Por que hace falta. El motor buscaba la foto de cada nota en Openverse, y
desde los servidores de GitHub esa API no responde dentro del tiempo de
espera. Como la regla es que sin foto la nota no se publica, el 20 de
octubre el motor escribio dos notas, no consiguio foto para ninguna y las
dos se perdieron; el workflow se reporto exitoso habiendo publicado cero.

La salida no es subir el tiempo de espera y rezar: es no depender de
internet para algo que ya tenemos. Estas fotos quedan EN el repositorio,
asi que el motor siempre encuentra una.

La seleccion es a ojo, mirando una hoja de contacto. No por nombre de
archivo ni por tamano: la primera vez que se eligio por tamano, una nota
de lavamanos abrio con la foto de una sala.
"""
from __future__ import annotations

import io
import json
import pathlib
import sys

from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ARCHIVO = pathlib.Path(
    r"C:\Users\jemho\Downloads\Revista remodelar\Revista remodelar\material\revista 0")
RAIZ = pathlib.Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "sitegen" / "static" / "propias"
CATALOGO = RAIZ / "data" / "fotos_propias.json"

# Por seccion, los indices elegidos mirando la hoja de contacto. El indice
# es la posicion en la lista de las 16 mas pesadas de la seccion, que es
# como se armo la hoja; `_fotos` reproduce ese mismo orden.
#
# El tema tiene que llamarse igual que una categoria o una ruta de
# config/rutas.yaml: asi es como el motor empareja la nota con la foto.
SELECCION = [
    # Baneras y espejos: lo unico de la seccion que es de bano de verdad.
    ("27_", "banos", [9, 10]),
    # Obra en bruto: escombros, sacos, paredes picadas, pintores.
    ("27_", "diseno", [0, 1, 2, 6, 8]),
    # Lamparas encendidas y luz de color: el corazon de la seccion.
    ("17_", "iluminacion", [11, 12, 9, 10, 4, 6]),
    ("17_", "cocinas", [5, 7]),
    # Plantas de interior, que es de lo que mas hay en el moodboard.
    ("30_", "jardines", [2, 4, 5, 6, 7, 11, 12]),
    # Texturas de piedra y concreto, para notas de material.
    ("30_", "pisos", [1, 3, 13]),
]

CREDITO = "Archivo Revista Remodelar"
ANCHO = 1400


def _carpeta(prefijo: str) -> pathlib.Path | None:
    for d in sorted(ARCHIVO.iterdir()):
        if d.is_dir() and d.name.startswith(prefijo):
            return d
    return None


def _fotos(d: pathlib.Path) -> list[pathlib.Path]:
    return sorted(
        (f for f in d.rglob("*")
         if f.suffix.lower() in (".jpg", ".jpeg") and not f.name.startswith("._")),
        key=lambda f: f.stat().st_size, reverse=True)[:16]


def main() -> int:
    if not ARCHIVO.exists():
        print(f"No esta el archivo en:\n  {ARCHIVO}")
        return 1

    DESTINO.mkdir(parents=True, exist_ok=True)
    catalogo: list[dict] = []
    if CATALOGO.exists():
        # Lo que ya hubiera (fotos de la feria, de tiendas) no se pisa.
        catalogo = [c for c in json.loads(CATALOGO.read_text(encoding="utf-8"))
                    if not c.get("del_archivo")]

    for prefijo, tema, indices in SELECCION:
        d = _carpeta(prefijo)
        if not d:
            print(f"  falta la seccion {prefijo}")
            continue
        fotos = _fotos(d)
        for i in indices:
            if i >= len(fotos):
                print(f"  {tema}: no existe el indice {i} en {prefijo}")
                continue
            f = fotos[i]
            nombre = f"{tema}-{prefijo.strip('_')}-{i:02d}.jpg"
            im = Image.open(f)
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            apaisada = im.width >= im.height
            if im.width > ANCHO:
                im.thumbnail((ANCHO, ANCHO * 3), Image.LANCZOS)
            im.save(DESTINO / nombre, "JPEG", quality=82,
                    optimize=True, progressive=True)
            catalogo.append({
                "tema": tema,
                "url": f"static/propias/{nombre}",
                "credito": CREDITO,
                "apaisada": apaisada,
                "origen": f.name,
                "del_archivo": True,
            })

    CATALOGO.parent.mkdir(parents=True, exist_ok=True)
    CATALOGO.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    por_tema: dict[str, int] = {}
    for c in catalogo:
        por_tema[c["tema"]] = por_tema.get(c["tema"], 0) + 1
    print(f"{len(catalogo)} fotos en el catalogo:")
    for t, n in sorted(por_tema.items()):
        print(f"   {n:>3}  {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
