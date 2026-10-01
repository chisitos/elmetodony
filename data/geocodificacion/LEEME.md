# Geocodificación — trabajo en curso

**Estado al 29 sep 2026: obtenido pero NO aplicado a `data/tiendas.yaml`.**

`geocodificar.py` usa **Photon** (Komoot), que sí entiende la nomenclatura
colombiana y llega a nivel de placa. Sin llave, sin costo, sin tarjeta.

Resultado: 54 de 55 tiendas, pero con calidad despareja. `resultado.json`
trae un campo `calidad` por tienda:

| calidad  | qué significa                                   | usable |
| -------- | ----------------------------------------------- | ------ |
| `exacta` | la placa de OSM coincide con la buscada          | sí     |
| `cuadra` | placa cercana en la misma vía (<60 de diferencia)| sí     |
| `via`    | acertó la vía, no la placa                       | dudoso |
| `zona`   | sólo el municipio o el barrio                    | no     |
| `DUDOSA` | cayó en el mismo punto que otra tienda distinta  | **no** |

Las `DUDOSA` son relleno del geocodificador: seis tiendas distintas
quedaron en un mismo punto de la Carrera 52, lo cual es imposible. Hay que
descartarlas.

**IDEO salió 8/8** con 170 m de dispersión. Como los 8 locales están en el
mismo edificio, deberían compartir un único punto: conviene fijar uno solo
a mano y asignárselo a los ocho.

## Antes de aplicarlo

1. Descartar `DUDOSA` y `zona`.
2. Fijar el punto único de IDEO.
3. Volcar `lat`/`lng` a `data/tiendas.yaml` sólo para las confiables.
4. `python run.py --site-only` — el mapa se enciende solo en las rutas que
   lleguen a dos paradas con coordenadas.

**Trampa:** no agregar `lang` a la consulta de Photon; responde 400.
Nominatim no sirve para esto, ya se descartó tres veces (ver CREDITOS.md).
