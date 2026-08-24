"""Remodelar — motor editorial para arquitectura interior y remodelación.

Pipeline de agentes:
  1. sources_rss   -> agente investigador de catálogo (RSS de medios de referencia)
  2. sources_web   -> agente investigador de exploración (búsqueda web con Claude)
  3. curator       -> agente curador/filtro (novedad, actualidad, utilidad,
                       materiales, tendencia)
  4. editor        -> agente editor (reescribe con la voz de Remodelar)
  5. sitegen.generate -> arma el sitio estático a partir de los artículos publicados
"""
