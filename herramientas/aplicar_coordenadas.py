# -*- coding: utf-8 -*-
"""Vuelca a data/tiendas.yaml las coordenadas de data/geocodificacion/.

Sólo las de calidad `exacta` y `cuadra`. Se descartan:

- `DUDOSA`: varias tiendas distintas cayeron en un mismo punto, que es
  relleno del geocodificador — imposible en la realidad.
- `zona` y `via`: sólo acertaron el municipio o la vía, no el local.

Precisión suficiente: el mapa es para orientarse, no para navegar. El
"Cómo llegar" sigue mandando la dirección en texto a Google, que resuelve
la nomenclatura colombiana con exactitud.
"""
from __future__ import annotations

import io
import json
import pathlib
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TIENDAS = RAIZ / "data" / "tiendas.yaml"
GEO = RAIZ / "data" / "geocodificacion" / "resultado.json"

USABLES = {"exacta", "cuadra"}

# Los 8 locales de IDEO están en el MISMO edificio: comparten un punto.
# Photon los resolvió todos a la Carrera 42 75-125, a media cuadra de la
# 75-83 real. Se fija uno solo para los ocho, interpolado entre los dos
# puntos que sí verificó en esa cuadra (75-13 y 75-125).
IDEO = (6.182900, -75.590900)


def main() -> int:
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    lineas = TIENDAS.read_text(encoding="utf-8").split("\n")

    salida: list[str] = []
    slug = None
    puestas = 0
    saltadas: list[str] = []

    for linea in lineas:
        m = re.match(r"^  - slug: (\S+)", linea)
        if m:
            slug = m.group(1)
        salida.append(linea)

        # Las coordenadas van después de la zona, que es donde se lee natural.
        if slug and re.match(r"^    zona: ", linea):
            if slug.endswith("-ideo"):
                lat, lng = IDEO
                salida += [f"    lat: {lat}", f"    lng: {lng}"]
                puestas += 1
            else:
                d = geo.get(slug)
                if d and d.get("calidad") in USABLES:
                    salida += [f"    lat: {d['lat']}", f"    lng: {d['lng']}"]
                    puestas += 1
                else:
                    saltadas.append(f"{slug} ({d['calidad'] if d else 'sin dato'})")

    TIENDAS.write_text("\n".join(salida), encoding="utf-8")
    print(f"coordenadas puestas: {puestas}")
    print(f"sin coordenadas:     {len(saltadas)}")
    for s in saltadas:
        print(f"   {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
