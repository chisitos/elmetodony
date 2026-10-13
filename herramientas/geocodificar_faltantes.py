# -*- coding: utf-8 -*-
"""Segundo intento para las tiendas que quedaron sin coordenadas.

El primer pase descartó 26 por caer varias en un mismo punto. Ese filtro
era necesario —seis tiendas distintas en la Carrera 52 es relleno— pero
demasiado grueso: tiendas que SÍ están juntas, como las cuatro de
iluminación de la Cra. 43A de Envigado, caían con ellas.

Acá el criterio es otro y más exacto: se acepta un resultado sólo si la
VÍA que devuelve Photon coincide con la vía de la dirección. Si busco
"Carrera 43A 31A Sur-25" y me responde con una Carrera 52, se descarta,
por buena que parezca la coincidencia.
"""
from __future__ import annotations

import io
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TIENDAS = RAIZ / "data" / "tiendas.yaml"
SALIDA = RAIZ / "data" / "geocodificacion" / "segundo-pase.json"

UA = {"User-Agent": "Remodelar/1.0 (https://feriaremodelar.com)"}
ABREV = [("Cra.", "Carrera"), ("Cl.", "Calle"), ("Av.", "Avenida"),
         ("CC ", "Centro Comercial ")]


def sin_tildes(s: str) -> str:
    d = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in d if unicodedata.category(c) != "Mn").lower()


def via_de(direccion: str) -> str | None:
    """'Cra. 43A #31A Sur-25, Envigado' -> 'carrera 43a'."""
    d = direccion
    for a, b in ABREV:
        d = d.replace(a, b)
    m = re.match(r"\s*(carrera|calle|avenida|circular|transversal|diagonal)\s+([0-9]+[a-z]?)",
                 sin_tildes(d))
    return f"{m.group(1)} {m.group(2)}" if m else None


def buscar(consulta: str, limite: int = 10) -> list[dict]:
    # OJO: nada de `lang`, Photon responde 400.
    url = "https://photon.komoot.io/api/?" + urllib.parse.urlencode(
        {"q": consulta, "limit": limite})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return json.loads(r.read().decode()).get("features", [])


def en_el_valle(lat: float, lon: float) -> bool:
    return 6.05 <= lat <= 6.45 and -75.78 <= lon <= -75.40


def main() -> int:
    datos = yaml.safe_load(TIENDAS.read_text(encoding="utf-8"))
    faltan = [t for t in datos["tiendas"] if not t.get("lat")]
    print(f"sin coordenadas: {len(faltan)}\n")

    resultados: dict[str, dict] = {}
    for t in faltan:
        via = via_de(t["direccion"])
        if not via:
            print(f"  SIN VIA   {t['slug']:<28} {t['direccion'][:40]}")
            continue

        limpia = t["direccion"]
        for a, b in ABREV:
            limpia = limpia.replace(a, b)
        limpia = limpia.replace("#", " ")

        elegido = None
        for consulta in (limpia, f"{t['nombre']}, {t['zona_nombre'] if 'zona_nombre' in t else ''} Medellín"):
            try:
                for c in buscar(consulta):
                    lon, lat = c["geometry"]["coordinates"]
                    if not en_el_valle(lat, lon):
                        continue
                    calle = sin_tildes(c["properties"].get("street", ""))
                    # El filtro que importa: la vía tiene que ser la misma.
                    if calle and via in calle:
                        elegido = (lat, lon, c["properties"])
                        break
            except Exception:
                pass
            time.sleep(0.5)
            if elegido:
                break

        if elegido:
            lat, lon, p = elegido
            placa = p.get("housenumber", "")
            resultados[t["slug"]] = {"lat": round(lat, 6), "lng": round(lon, 6),
                                     "via": p.get("street", ""), "placa": placa}
            print(f"  OK        {t['slug']:<28} {lat:.5f},{lon:.5f}  "
                  f"{p.get('street','')} {placa}")
        else:
            print(f"  NO CUADRA {t['slug']:<28} esperaba '{via}'")

    SALIDA.write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nrecuperadas: {len(resultados)} de {len(faltan)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
