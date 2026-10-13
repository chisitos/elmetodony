# -*- coding: utf-8 -*-
"""Completa las coordenadas que faltan, marcándolas como aproximadas.

Por qué hace falta: OpenStreetMap no tiene las placas de la mayoría de las
direcciones de Medellín. Tras dos pases de geocodificación quedaron 22
tiendas sin ubicar, y sin ellas una ruta de cinco paradas mostraba tres: no
se leía como un recorrido.

Qué hace: a las que faltan les asigna el centro de las tiendas YA
VERIFICADAS de su misma zona, y las marca `aprox: true`. El mapa las dibuja
distinto y su globo lo advierte; el enlace "Cómo llegar" sigue mandando la
dirección en texto a Google, que sí resuelve la nomenclatura colombiana.

Es una posición de orientación, no de navegación. La distinción tiene que
quedar visible en el mapa: un punto exacto y uno aproximado no pueden
parecer lo mismo.
"""
from __future__ import annotations

import io
import json
import pathlib
import re
import sys

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TIENDAS = RAIZ / "data" / "tiendas.yaml"
SEGUNDO = RAIZ / "data" / "geocodificacion" / "segundo-pase.json"


def main() -> int:
    datos = yaml.safe_load(TIENDAS.read_text(encoding="utf-8"))
    recuperadas = json.loads(SEGUNDO.read_text(encoding="utf-8")) if SEGUNDO.exists() else {}

    # Centro de cada zona, a partir de lo ya verificado. Si una zona no tiene
    # ninguna verificada, no se inventa: esas quedan sin coordenada.
    por_zona: dict[str, list[tuple[float, float]]] = {}
    for t in datos["tiendas"]:
        if t.get("lat") and not t.get("aprox"):
            por_zona.setdefault(t["zona"], []).append((t["lat"], t["lng"]))
    centros = {z: (round(sum(p[0] for p in v) / len(v), 6),
                   round(sum(p[1] for p in v) / len(v), 6))
               for z, v in por_zona.items()}
    print("centros por zona (de tiendas verificadas):")
    for z, c in sorted(centros.items()):
        print(f"   {z:<10} {c[0]:.5f},{c[1]:.5f}   ({len(por_zona[z])} verificadas)")

    lineas = TIENDAS.read_text(encoding="utf-8").split("\n")
    salida: list[str] = []
    slug = zona = None
    exactas = aprox = sin_nada = 0

    for linea in lineas:
        m = re.match(r"^  - slug: (\S+)", linea)
        if m:
            slug, zona = m.group(1), None
        mz = re.match(r"^    zona: (\S+)", linea)
        if mz:
            zona = mz.group(1)
        salida.append(linea)

        if slug and mz:
            tienda = next(t for t in datos["tiendas"] if t["slug"] == slug)
            if tienda.get("lat"):
                exactas += 1
                continue
            if slug in recuperadas:
                r = recuperadas[slug]
                salida += [f"    lat: {r['lat']}", f"    lng: {r['lng']}"]
                exactas += 1
            elif zona in centros:
                lat, lng = centros[zona]
                salida += [f"    lat: {lat}", f"    lng: {lng}", "    aprox: true"]
                aprox += 1
            else:
                sin_nada += 1

    TIENDAS.write_text("\n".join(salida), encoding="utf-8")
    print(f"\nverificadas: {exactas}   aproximadas: {aprox}   sin ubicar: {sin_nada}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
