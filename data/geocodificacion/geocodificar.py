# -*- coding: utf-8 -*-
"""Geocodifica con Photon (Komoot). Sin llave, sin costo, sin tarjeta.

Photon sí entiende la nomenclatura colombiana y llega a nivel de placa,
a diferencia de Nominatim. Cuando la placa exacta no está en OSM, se elige
entre los candidatos de la misma vía el de número más cercano — para un
mapa de orientación, media cuadra de error no cambia nada, y el "Cómo
llegar" sigue yendo por texto a Google, que resuelve exacto.

OJO: el parámetro `lang` hace que Photon responda 400. No agregarlo.
"""
import sys, io, json, time, urllib.parse, urllib.request, pathlib, re
import yaml
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ABREV = [("Cra.", "Carrera"), ("Cl.", "Calle"), ("Av.", "Avenida"),
         ("CC ", "Centro Comercial "), ("#", " ")]
VALLE = lambda la, lo: 6.05 <= la <= 6.45 and -75.78 <= lo <= -75.40

def limpiar(d):
    for a, b in ABREV:
        d = d.replace(a, b)
    return re.sub(r"\s+", " ", d).strip()

def num_placa(s):
    """'75-83' -> 75. Sirve para comparar cuál candidato está más cerca."""
    m = re.search(r"(\d+)", s or "")
    return int(m.group(1)) if m else None

def buscar(q, limite=8):
    url = "https://photon.komoot.io/api/?" + urllib.parse.urlencode({"q": q, "limit": limite})
    req = urllib.request.Request(url, headers={"User-Agent": "Remodelar/1.0 (directorio Medellin)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode()).get("features", [])

datos = yaml.safe_load(pathlib.Path("data/tiendas.yaml").read_text(encoding="utf-8"))
res, sin = {}, []

for t in datos["tiendas"]:
    dir_limpia = limpiar(t["direccion"])
    objetivo = num_placa(t["direccion"].split("#")[-1]) if "#" in t["direccion"] else None
    mejor, mejor_dif, calidad = None, 10**9, "?"
    for intento in (dir_limpia, dir_limpia + ", Colombia", limpiar(t["nombre"]) + ", Medellín, Colombia"):
        try:
            f = buscar(intento)
        except Exception:
            f = []
        time.sleep(0.5)
        for c in f:
            lo, la = c["geometry"]["coordinates"]
            if not VALLE(la, lo):
                continue
            p = c["properties"]
            hn = num_placa(p.get("housenumber"))
            dif = abs(hn - objetivo) if (hn and objetivo) else (500 if hn else 900)
            if dif < mejor_dif:
                mejor_dif, mejor = dif, (round(la, 6), round(lo, 6), p)
                calidad = "exacta" if dif == 0 else ("cuadra" if dif < 60 else ("via" if dif < 800 else "zona"))
        if mejor and mejor_dif < 60:
            break
    if mejor:
        la, lo, p = mejor
        res[t["slug"]] = {"lat": la, "lng": lo, "calidad": calidad,
                          "match": " ".join(x for x in (p.get("street"), p.get("housenumber"), p.get("city")) if x)[:45]}
        print(f"{calidad:<7} {t['slug']:<28} {la:.5f},{lo:.5f}  {res[t['slug']]['match']}")
    else:
        sin.append(t["slug"]); print(f"{'NADA':<7} {t['slug']:<28} {dir_limpia[:42]}")

pathlib.Path("geo_photon.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
from collections import Counter
print("\n" + " | ".join(f"{k}: {v}" for k, v in Counter(v["calidad"] for v in res.values()).items()))
ideo = [v for k, v in res.items() if k.endswith("-ideo")]
if len(ideo) > 1:
    la = [v["lat"] for v in ideo]; lo = [v["lng"] for v in ideo]
    print(f"IDEO: {len(ideo)}/8, dispersión ~{max(max(la)-min(la), max(lo)-min(lo))*111:.2f} km")
print(f"TOTAL: {len(res)}/{len(datos['tiendas'])}  sin ubicar: {len(sin)}")
