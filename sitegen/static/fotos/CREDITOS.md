# Fotos de ambiente — origen y licencia

Estas imágenes vienen de **Unsplash** y se usan bajo la
[licencia de Unsplash](https://unsplash.com/license): uso comercial
permitido, sin pago y sin atribución obligatoria. Es decir, no son sólo para
maquetear: pueden quedarse en producción.

## Regla de uso

Ilustran **una categoría**, nunca un establecimiento. La foto de `bano.jpg`
dice "esta ruta es de baños"; no dice ni insinúa que así se vea D&D Colombia
ni ninguna otra tienda del directorio.

Por eso:

- Las **rutas** llevan foto de ambiente. ✅
- Las **fichas de tienda** NO llevan foto de ambiente. ❌
  Poner un baño genérico en la ficha de una tienda real da a entender que es
  su local o su producto, y eso es tergiversar un negocio ajeno. La ficha
  sólo puede llevar foto propia: logo o fotografía que el establecimiento
  entregue.
- **IDEO** tampoco lleva foto de archivo, por lo mismo. Es un lugar real,
  con una fachada concreta sobre la Autopista Sur. Va con su identidad
  gráfica hasta que haya fotografía real del centro comercial.

## Archivos

Cada ruta tiene dos tamaños: `<nombre>.jpg` (1200×520, cabecera y tarjeta) y
`<nombre>-sm.jpg` (200×150, miniatura del menú lateral).

| Archivo       | Ruta                    | Qué muestra                     |
| ------------- | ----------------------- | ------------------------------- |
| `bano`        | Remodelar el baño       | Bañera y lavamanos              |
| `cocina`      | Cocina integral         | Cocina con gabinetes oscuros    |
| `pisos`       | Cambiar los pisos       | Corredor con piso de madera     |
| `apartamento` | Apartamento desde cero  | Sala-comedor abierta            |
| `iluminacion` | Iluminar la casa        | Colgantes de cobre              |
| `sala`        | Sala y comedor          | Sala con sofá azul              |
| `terraza`     | Terraza y jardín        | Casa blanca con jardín          |
| `infantil`    | Cuarto infantil         | Juguetes de madera              |
| `tech`        | Casa inteligente        | Cerradura inteligente y celular |

## Reemplazar una foto

Dejá el archivo con el mismo nombre en esta carpeta, en los dos tamaños, y
corré `python run.py --site-only`. La asociación ruta→foto está en el campo
`foto:` de cada ruta en `config/rutas.yaml`.

---

## Coordenadas para el mapa de rutas

El mapa de cada ruta aparece cuando **al menos dos** de sus paradas
principales tienen `lat` y `lng` en `data/tiendas.yaml`:

```yaml
  - slug: decorceramica-ideo
    nombre: Decorcerámica
    zona: ideo
    lat: 6.173900
    lng: -75.593600
```

Sin coordenadas la ruta muestra la foto de cabecera, como hasta ahora. Se
pueden ir cargando de a poco: cada ruta se enciende sola al llegar a dos.

**Cómo sacarlas:** abrir Google Maps, clic derecho sobre el local, y la
primera línea del menú son las coordenadas — clic las copia. Van en ese
orden: latitud primero, longitud después (negativa en Colombia).

**IDEO rinde más que ninguna:** un solo punto sirve para sus 8 locales, y
son la mayoría de las paradas de las rutas de obra.

**Por qué no están ya:** se intentó geocodificar automáticamente contra
Nominatim (OpenStreetMap) tres veces — por dirección, con caja delimitadora
al Valle de Aburrá, y por nombre de negocio. OSM no tiene las placas
colombianas: devuelve el punto medio de la carrera, así que los 8 locales de
IDEO caían en tres sitios distintos y ninguno en la Autopista Sur. Por
nombre sólo encuentra cadenas grandes (Homecenter, IKEA). Para automatizarlo
haría falta la API de Google, que sí resuelve nomenclatura colombiana.
