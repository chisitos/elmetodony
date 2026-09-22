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
