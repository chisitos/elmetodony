# Remodelar

Guía de compra para remodelar en Medellín, y motor editorial automatizado de
arquitectura interior. Dos mitades que comparten sitio, plantilla y voz:

- **Rutas y directorio** — 55 tiendas verificadas y 9 **Rutas Remodelar** que
  las ordenan en el orden real de la obra, con IDEO (Autopista Sur) como
  ancla. Sale de archivos YAML, no gasta tokens.
- **La revista** — un equipo de agentes investiga, filtra por relevancia y
  redacta con voz propia — vanguardista, precisa, sin relleno — y publica
  **ediciones semanales**, con imagen en cada nota.

El sitio es estático y PWA instalable: la ruta se hace caminando, con el
celular en la mano y a veces sin señal.

Tres reglas de fondo, no negociables:

- **Nunca repite.** El curador ve todo lo publicado recientemente y descarta
  cualquier historia o ángulo que ya haya salido, aunque venga de otra fuente.
- **Calidad sobre cantidad.** El tope de notas por edición es un techo, no un
  objetivo. Una edición de 3 piezas muy buenas es mejor que una de 8 con relleno.
- **Es una publicación visual.** Cada nota busca imagen real del thumbnail
  que el propio RSS publica para sindicación; si no hay, completa con una
  foto ilustrativa de banco libre (marcada como tal); si tampoco hay, se
  resuelve con una placa de trama técnica prolija, nunca con un ícono roto.

## Cómo funciona (5 agentes + generador de sitio)

```
┌─────────────────┐   ┌──────────────────┐
│ Investigador RSS │   │ Investigador Web  │   agentes de investigación:
│ (feeds de medios │   │ (Claude + búsqueda│   traen candidatos crudos,
│  de referencia,  │   │  web nativa)      │   cada uno con su imagen si
│  con su imagen)  │   │                   │   la encuentra (RSS u og:image)
└────────┬─────────┘   └────────┬─────────┘
         └──────────┬───────────┘
                     ▼
              ┌─────────────┐
              │   Curador   │   filtra por: novedad (incluye "¿ya lo publicamos?"),
              │  (filtro de │   actualidad, utilidad, uso de materiales, tendencia
              │ relevancia) │   de industria, encaje temático — nunca repite
              └──────┬──────┘
                     ▼
              ┌─────────────┐
              │   Editor    │   reescribe con la voz de Remodelar (config/editorial.yaml),
              │ (voz propia)│   nunca inventa datos, siempre cita la fuente
              └──────┬──────┘
                     ▼
     data/articles/*.json → sitegen/generate.py → public/ (edición semanal + archivo)
```

- **`pipeline/sources_rss.py`** — lee los feeds de `config/feeds.yaml` (Dezeen,
  designboom, ArchDaily, Design Milk, Yellowtrace, The Spaces, Interior
  Design, Architectural Digest), filtra por las palabras clave de
  `config/editorial.yaml → scope` y extrae el thumbnail de sindicación del
  propio item (`pipeline/images.py`). Determinístico, no gasta tokens.
- **`pipeline/sources_web.py`** — agente que usa la tool de búsqueda web
  nativa de Claude para encontrar lo que los feeds fijos no cubren
  (lanzamientos de materiales, tendencias emergentes), con fallback de
  imagen vía `og:image` de la página encontrada.
- **`pipeline/stock_images.py`** — si ni el RSS ni la búsqueda web trajeron
  imagen, completa con una foto ilustrativa de banco libre (Openverse,
  licencias reusables) — ver "Imágenes y derechos de autor" más abajo.
- **`pipeline/curator.py`** — agente que puntúa cada candidato en el rubro
  editorial, ve las últimas ~40 notas publicadas para no repetir historia
  ni ángulo, y selecciona sólo los que superan el umbral
  (`min_score_to_select`), hasta un tope por edición (`max_selected_per_run`
  — un techo, no una meta).
- **`pipeline/editor.py`** — agente que reescribe cada candidato seleccionado
  con la voz de Remodelar. La guía de voz completa vive en
  `config/editorial.yaml → voice` y se inyecta tal cual en el prompt.
- **`sitegen/generate.py`** — arma el sitio completo: la portada, las rutas,
  el directorio, la página de IDEO y la revista (`public/revista/`,
  `public/ediciones/`, `public/articulos/`).
- **`sitegen/directorio.py`** — carga `data/tiendas.yaml` y `config/rutas.yaml`
  y resuelve cada parada de cada ruta a la tienda concreta. Sólo depende de
  PyYAML: corre en `--site-only` sin tocar la API.

Todo el criterio editorial (fuentes, alcance temático, pesos del rubro, tono,
frases prohibidas, cuánto mirar hacia atrás para no repetir) vive en
`config/*.yaml` — cambiar el comportamiento no requiere tocar código.

## Uso local

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python run.py                 # corre los agentes + regenera el sitio
python run.py --site-only     # sólo regenera public/ desde data/articles/ (sin API)
python -m http.server -d public 8000   # ver el sitio en localhost:8000
```

`run.py --site-only` no llama a la API — sirve para iterar el diseño del
sitio o previsualizar ediciones ya publicadas sin gastar tokens.

## Puesta en producción (GitHub Actions + Pages)

1. **Secret**: en el repo, Settings → Secrets and variables → Actions →
   agregar `ANTHROPIC_API_KEY` con tu API key de Anthropic.
2. **Pages**: Settings → Pages → Source → "GitHub Actions".
3. El workflow `.github/workflows/publish.yml` corre **una vez por semana**
   (lunes 13:00 UTC / 08:00 hora de Colombia), o manualmente desde la pestaña Actions
   ("Run workflow"). Cada corrida:
   - corre el pipeline de agentes, que arma la edición de esa semana,
   - commitea los artículos nuevos a `data/articles/` (historial versionado
     de todo lo publicado, y la base con la que el curador evita repetirse),
   - regenera y publica el sitio en GitHub Pages.
4. Ajuste el día/horario editando el `cron` del workflow, y el volumen/
   criterio editando `config/editorial.yaml`.

**Costo**: cada corrida hace llamadas reales a la API de Claude (investigador
web, curador, editor por cada nota seleccionada). Con la config por defecto
(techo de 8 notas por edición semanal) el consumo es acotado, pero corra
`python run.py` localmente primero para calibrar `min_score_to_select` y
`max_selected_per_run` a tu gusto antes de dejarlo en automático.

## Rutas y directorio

Además de la revista, el sitio es una **guía de compra de Medellín**: 55
tiendas verificadas y 9 rutas que las ordenan en el orden real de la obra.

- `data/tiendas.yaml` — el directorio. Nombre, categorías, dirección, zona,
  nivel de precio y si está en IDEO. Editarlo cambia el directorio, las rutas
  y el buscador sin tocar código.
- `config/rutas.yaml` — las rutas. Cada parada define una categoría, qué
  buscar, un consejo práctico y las tiendas candidatas (la primera es la
  recomendada, el resto alternativas).

**IDEO (Autopista Sur, Itagüí) es el ancla del ecosistema.** Concentra los 8
locales de obra — pisos, enchapes, sanitarios, grifería, cocinas y
electrodomésticos — así que toda ruta de obra arranca ahí y después sale a
completar decoración en Envigado, Poblado o Laureles. Ese criterio está
escrito arriba de `config/rutas.yaml` y es lo que define qué tienda va
primero en cada parada.

El buscador del directorio corre entero en el navegador contra las filas ya
renderizadas (`sitegen/static/buscador.js`): funciona sin conexión y sin
servidor. El sitio es además una PWA instalable, porque la ruta se hace
caminando y con mala señal.

## Imágenes y derechos de autor

Remodelar nunca aloja ni redistribuye fotos ajenas: cada nota referencia
(`hotlink`) la imagen desde el servidor del medio original, con crédito
visible ("Imagen: {fuente}") y link a la fuente al pie — nunca se descarga
ni se sirve una copia desde acá. Achicar el tamaño en pantalla con CSS no
cambia nada legalmente si el archivo de origen es el mismo; lo que importa
es qué archivo se pide, no a qué tamaño se pinta. Por eso hay dos niveles,
con riesgo muy distinto, y el pipeline los trata distinto (`pipeline/images.py`):

1. **RSS-only para el agente de RSS** (`sources_rss.py`): sólo usa el
   thumbnail que el propio feed publica para sindicación (`media:content`,
   `media:thumbnail`, enclosure, o el primer `<img>` del post) — típicamente
   un derivado chico (400-500px) que el medio arma a propósito para esto
   (ej. la carpeta `/newsletter/` de ArchDaily). Es el nivel de riesgo bajo:
   un archivo ofrecido específicamente para que un lector de feeds lo
   muestre. **No hay fallback a la foto grande de portada** — si el feed no
   trae thumbnail, la nota queda sin foto.
2. **`og:image` sólo como último recurso para el agente de búsqueda web**
   (`sources_web.py`): una nota que no vino de un RSS no tiene thumbnail de
   sindicación disponible, así que ahí sí se usa el `og:image`/`twitter:image`
   de la página — normalmente la foto grande pensada para redes, no para
   esto. Es un nivel de riesgo más alto a propósito acotado a la minoría del
   feed que viene de búsqueda web, nunca a la base de fuentes RSS.
3. **Foto ilustrativa de banco libre, si los dos niveles anteriores no
   encontraron nada** (`pipeline/stock_images.py`): busca en Openverse
   (agregador de Creative Commons de Flickr, Wikimedia Commons, etc., API
   pública sin key) una foto genérica por categoría, filtrada a licencias
   que permiten uso comercial y modificación (CC0, CC BY, CC BY-SA — nunca
   NC/ND), con autor y licencia guardados para atribuir. Esto es **siempre
   una foto genérica, nunca del proyecto real de la nota** — por eso el
   sitio la marca con un badge "Imagen ilustrativa" sobre la foto, y en la
   página del artículo el crédito dice explícitamente "no es una foto del
   proyecto" en vez de "Imagen: {fuente}".

Cuando ninguno de los tres niveles encuentra nada, la nota se resuelve con
una placa de trama técnica (el hatching de un plano de obra) en vez de un
ícono de imagen rota — nunca se inventa una foto para una nota real.

### Excepción: las fotos de las rutas

Todo lo anterior vale para **la revista**, donde la foto pertenece a un medio
ajeno. Las **rutas** son otra cosa y sí alojan su imagen
(`sitegen/static/fotos/`): son nueve fotos de Unsplash, cuya
[licencia](https://unsplash.com/license) permite explícitamente descargar,
alojar y usar comercialmente, sin atribución obligatoria. No hay hotlink que
respetar porque no se está usando el servidor de ningún medio.

La regla dura acá es otra, y es de honestidad más que de derechos:

> Una foto de banco ilustra **una categoría**, nunca un establecimiento.

Por eso `fotos/bano.jpg` encabeza la Ruta Baños, pero **ninguna ficha de
tienda lleva foto de banco**: poner un baño genérico en la ficha de D&D
Colombia da a entender que así es su local, y eso tergiversa un negocio real.
**IDEO tampoco lleva foto de archivo** — es un lugar concreto, con fachada
propia sobre la Autopista Sur, y va con su identidad gráfica hasta que haya
fotografía real. Fichas e IDEO sólo admiten imagen propia: logo o foto que el
establecimiento entregue.

Qué foto va en qué ruta, y cómo reemplazarlas, está en
`sitegen/static/fotos/CREDITOS.md`. La asociación vive en el campo `foto:` de
cada ruta en `config/rutas.yaml`; si una ruta no lo tiene, cae sola en la
placa de trama.

> Pendiente de decisión: el pipeline ya usa **Openverse** (CC, con autor y
> licencia guardados) como banco libre para la revista. Las fotos de ruta
> podrían migrarse ahí por consistencia; se eligió Unsplash porque no exige
> atribución visible y las nueve se revisaron una por una antes de asignarlas.

Esto no es asesoría legal. El texto de cada nota es reescritura editorial
original (bajo riesgo); las fotos son lo más sensible del sistema — si este
proyecto crece a algo público/comercial de verdad, vale una revisión legal
puntual sobre el uso de imagen antes de escalarlo.

## Contenido de muestra

`data/articles/` trae la primera edición real de Remodelar: 5 notas
curadas a mano sobre RSS reales de los medios de `config/feeds.yaml`
(designboom, Yellowtrace, Design Milk, ArchDaily), redactadas en la voz de
Remodelar y fundamentadas estrictamente en lo que cada fuente publicó —
sin inventar datos. Cada una lleva su **imagen real** (la que trae el
propio feed o la página del artículo) y su **atribución con link** a la
fuente original, visible al pie de la nota.

Esta tanda se armó a mano (por Claude, en esta conversación) porque esta
sesión no tiene una `ANTHROPIC_API_KEY` propia para invocar a los agentes
curador/editor vía API — se usó el mismo agente investigador de RSS del
pipeline (`pipeline/sources_rss.py`) para traer los candidatos reales, y
después se escribió cada nota siguiendo el mismo criterio y la misma guía
de voz que usan los agentes. Una vez que configures el secret
`ANTHROPIC_API_KEY` (ver más abajo), las próximas ediciones las arma el
pipeline solo. Si prefiere arrancar de cero, borre los `.json` de
`data/articles/` y `data/seen.json`.

## Editar el tono o el criterio

- **Tono / voz**: `config/editorial.yaml → voice.principles` y
  `forbidden_phrases`. Se inyecta literal en el system prompt del editor.
- **Qué cuenta como relevante y "no repetido"**: `config/editorial.yaml →
  scope`, `rubric.weights` y `run.dedup_lookback_articles`.
- **Tamaño de la edición**: `run.max_selected_per_run` (techo) y
  `run.min_score_to_select` (umbral de calidad).
- **Fuentes RSS**: `config/feeds.yaml` — agregar o sacar un feed es una
  línea, no requiere tocar código.
- **Nombre de la publicación**: `config/editorial.yaml → publication.name`.

## Sobre atribución

Remodelar no republica texto ajeno: cada nota es una reescritura editorial
original, fundamentada estrictamente en el resumen/fuente disponible, con
atribución y enlace visible a la fuente original al pie de cada nota (ver
`pipeline/editor.py` y la caja de fuente en `sitegen/templates/article.html`).
Las imágenes se muestran igual que en cualquier previsualizador de links,
con crédito a la fuente visible debajo de la foto.
