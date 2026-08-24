# Remodelar

Motor editorial automatizado de arquitectura interior y remodelación de
espacios, hecho para diseñadores. Un equipo de agentes investiga, filtra por
relevancia y redacta con voz propia — vanguardista, precisa, sin relleno — y
publica **ediciones semanales** de un sitio editorial estático, con imagen
en cada nota.

Tres reglas de fondo, no negociables:

- **Nunca repite.** El curador ve todo lo publicado recientemente y descarta
  cualquier historia o ángulo que ya haya salido, aunque venga de otra fuente.
- **Calidad sobre cantidad.** El tope de notas por edición es un techo, no un
  objetivo. Una edición de 3 piezas muy buenas es mejor que una de 8 con relleno.
- **Es una publicación visual.** Cada nota busca imagen real (del RSS o de la
  página fuente) antes que texto solo; sin foto, se resuelve con una placa de
  trama técnica prolija, nunca con un ícono roto.

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
  `config/editorial.yaml → scope` y extrae la imagen del propio item
  (`pipeline/images.py`). Determinístico, no gasta tokens.
- **`pipeline/sources_web.py`** — agente que usa la tool de búsqueda web
  nativa de Claude para encontrar lo que los feeds fijos no cubren
  (lanzamientos de materiales, tendencias emergentes), con fallback de
  imagen vía `og:image` de la página encontrada.
- **`pipeline/curator.py`** — agente que puntúa cada candidato en el rubro
  editorial, ve las últimas ~40 notas publicadas para no repetir historia
  ni ángulo, y selecciona sólo los que superan el umbral
  (`min_score_to_select`), hasta un tope por edición (`max_selected_per_run`
  — un techo, no una meta).
- **`pipeline/editor.py`** — agente que reescribe cada candidato seleccionado
  con la voz de Remodelar. La guía de voz completa vive en
  `config/editorial.yaml → voice` y se inyecta tal cual en el prompt.
- **`sitegen/generate.py`** — agrupa lo publicado por semana calendario y arma
  el sitio: `public/index.html` (última edición), `public/ediciones/` (cada
  edición pasada + archivo), `public/articulos/` (cada nota).

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
   (lunes 11:00 UTC / 08:00 ART), o manualmente desde la pestaña Actions
   ("Run workflow"). Cada corrida:
   - corre el pipeline de agentes, que arma la edición de esa semana,
   - commitea los artículos nuevos a `data/articles/` (historial versionado
     de todo lo publicado, y la base con la que el curador evita repetirse),
   - regenera y publica el sitio en GitHub Pages.
4. Ajustá el día/horario editando el `cron` del workflow, y el volumen/
   criterio editando `config/editorial.yaml`.

**Costo**: cada corrida hace llamadas reales a la API de Claude (investigador
web, curador, editor por cada nota seleccionada). Con la config por defecto
(techo de 8 notas por edición semanal) el consumo es acotado, pero corré
`python run.py` localmente primero para calibrar `min_score_to_select` y
`max_selected_per_run` a tu gusto antes de dejarlo en automático.

## Imágenes

Cada candidato busca imagen en este orden: metadata del propio RSS
(`media:content`, `media:thumbnail`, enclosure, o el primer `<img>` del
post), y si no hay, un fetch liviano del `og:image`/`twitter:image` de la
página original — el mismo mecanismo que usa cualquier previsualizador de
links. Nunca se genera ni se inventa una imagen para una nota real. Cuando
no se encuentra ninguna, la nota se resuelve con una placa de trama técnica
(el hatching de un plano de obra) en vez de un ícono de imagen rota.

## Contenido de muestra

`data/articles/` ya trae 5 notas de muestra (escritas a mano, en la voz de
Remodelar, cubriendo remodelación, materiales, iluminación e interiorismo
comercial/residencial) para que puedas ver el sitio funcionando sin correr
el pipeline. Van sin imagen a propósito — son contenido inventado para la
demo (no hay foto real que les corresponda), así que muestran la placa de
respaldo; las notas reales que arme el pipeline sí van a traer foto. Si
preferís arrancar de cero, borrá los `.json` de `data/articles/` y
`data/seen.json`.

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
