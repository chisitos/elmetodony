# ALBA

Motor editorial automatizado de arquitectura interior y remodelación de
espacios. Un equipo de agentes investiga, filtra por relevancia y redacta
con voz propia — vanguardista, precisa, sin relleno — y publica un sitio
editorial estático.

## Cómo funciona (5 agentes)

```
┌─────────────────┐   ┌──────────────────┐
│ Investigador RSS │   │ Investigador Web  │   agentes de investigación:
│ (feeds de medios │   │ (Claude + búsqueda│   traen candidatos crudos
│  de referencia)  │   │  web nativa)      │
└────────┬─────────┘   └────────┬─────────┘
         └──────────┬───────────┘
                     ▼
              ┌─────────────┐
              │   Curador   │   filtra por: novedad, actualidad, utilidad,
              │  (filtro de │   uso de materiales, tendencia de industria,
              │ relevancia) │   encaje temático — score 0-10 ponderado
              └──────┬──────┘
                     ▼
              ┌─────────────┐
              │   Editor    │   reescribe con la voz de ALBA (config/editorial.yaml),
              │ (voz propia)│   nunca inventa datos, siempre cita la fuente
              └──────┬──────┘
                     ▼
              data/articles/*.json → sitegen/generate.py → public/ (sitio estático)
```

- **`pipeline/sources_rss.py`** — lee los feeds de `config/feeds.yaml` (Dezeen,
  designboom, ArchDaily, Design Milk, Yellowtrace, The Spaces, Interior
  Design, Architectural Digest), filtra por las palabras clave de
  `config/editorial.yaml → scope`. Determinístico, no gasta tokens.
- **`pipeline/sources_web.py`** — agente que usa la tool de búsqueda web
  nativa de Claude para encontrar lo que los feeds fijos no cubren
  (lanzamientos de materiales, tendencias emergentes).
- **`pipeline/curator.py`** — agente que puntúa cada candidato en el rubro
  editorial y selecciona sólo los que superan el umbral (`min_score_to_select`),
  hasta un tope por corrida (`max_selected_per_run`).
- **`pipeline/editor.py`** — agente que reescribe cada candidato seleccionado
  con la voz de ALBA. La guía de voz completa vive en
  `config/editorial.yaml → voice` y se inyecta tal cual en el prompt.
- **`sitegen/generate.py`** — arma el sitio estático (`public/index.html` +
  `public/articulos/*.html`) a partir de todo lo publicado en
  `data/articles/`.

Todo el criterio editorial (fuentes, alcance temático, pesos del rubro, tono,
frases prohibidas) vive en `config/*.yaml` — cambiar el comportamiento no
requiere tocar código.

## Uso local

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python run.py            # corre los 5 agentes + regenera el sitio
python run.py --site-only     # sólo regenera public/ desde data/articles/ (sin API)
python -m http.server -d public 8000   # ver el sitio en localhost:8000
```

`run.py --site-only` no llama a la API — sirve para iterar el diseño del
sitio o previsualizar artículos ya publicados sin gastar tokens.

## Puesta en producción (GitHub Actions + Pages)

1. **Secret**: en el repo, Settings → Secrets and variables → Actions →
   agregar `ANTHROPIC_API_KEY` con tu API key de Anthropic.
2. **Pages**: Settings → Pages → Source → "GitHub Actions".
3. El workflow `.github/workflows/publish.yml` corre todos los días a las
   11:00 UTC (08:00 ART), o manualmente desde la pestaña Actions
   ("Run workflow"). Cada corrida:
   - corre el pipeline de agentes,
   - commitea los artículos nuevos a `data/articles/` (así queda historial
     versionado de todo lo publicado),
   - regenera y publica el sitio en GitHub Pages.
4. Ajustá el horario editando el `cron` del workflow, y el volumen/criterio
   editando `config/editorial.yaml`.

**Costo**: cada corrida hace llamadas reales a la API de Claude (investigador
web, curador, editor por cada artículo seleccionado). Con la config por
defecto (`max_selected_per_run: 6`, corrida diaria) el consumo es acotado,
pero corré `python run.py` localmente primero para calibrar `min_score_to_select`
y `max_selected_per_run` a tu gusto antes de dejarlo en automático.

## Contenido de muestra

`data/articles/` ya trae 5 artículos de muestra (escritos a mano, en la voz
de ALBA, cubriendo remodelación, materiales, iluminación e interiorismo
comercial/residencial) para que puedas ver el sitio funcionando sin correr
el pipeline. La primera corrida real los va a acompañar; si preferís
arrancar de cero, borrá los `.json` de `data/articles/` y `data/seen.json`.

## Editar el tono o el criterio

- **Tono / voz**: `config/editorial.yaml → voice.principles` y
  `forbidden_phrases`. Se inyecta literal en el system prompt del editor.
- **Qué cuenta como relevante**: `config/editorial.yaml → scope` (palabras
  clave) y `rubric.weights` (qué tan estricto es el curador en cada eje).
- **Fuentes RSS**: `config/feeds.yaml` — agregar o sacar un feed es una
  línea, no requiere tocar código.
- **Nombre de la publicación**: `config/editorial.yaml → publication.name`.

## Sobre atribución

ALBA no republica texto ajeno: cada artículo es una reescritura editorial
original, fundamentada estrictamente en el resumen/fuente disponible, con
atribución y enlace visible a la fuente original al pie de cada nota (ver
`pipeline/editor.py` y la caja de fuente en `sitegen/templates/article.html`).
