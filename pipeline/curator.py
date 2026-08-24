"""Agente curador: filtra y puntúa los candidatos antes de pasarlos al editor.

Aplica el rubro de config/editorial.yaml (novedad, actualidad, utilidad, uso de
materiales, tendencia de industria, encaje temático) y devuelve sólo los que
superan el umbral, hasta el tope de artículos por corrida.
"""
from __future__ import annotations

import logging

from .config import Config
from .llm import call_json
from .models import Candidate, ScoredCandidate

log = logging.getLogger("alba.curator")

SYSTEM_TEMPLATE = """Sos el agente curador de ALBA, un medio editorial vanguardista de \
arquitectura interior y remodelación de espacios. Recibís una lista de candidatos \
(noticias/proyectos crudos) y tenés que decidir cuáles merecen convertirse en un \
artículo de ALBA.

Evaluá cada candidato en estos ejes, puntuando de 0 a 10 cada uno:
- novedad: ¿es genuinamente nuevo o ya se cubrió hasta el cansancio en otros medios?
- actualidad: ¿qué tan reciente es? Usá la fecha de publicación si está; si no está, \
asumí actualidad media (5) salvo que el contenido sugiera que es viejo.
- utilidad: ¿le sirve a alguien que está diseñando o remodelando un espacio real \
(ideas aplicables, no sólo estética)?
- uso_materiales: ¿hay especificidad real de materiales, técnicas o procesos, o es \
genérico ("materiales innovadores" sin decir cuáles)?
- tendencia_industria: ¿conecta con una tendencia real y verificable de la industria \
del diseño de interiores?
- encaje_tematico: ¿encaja con el alcance de ALBA (arquitectura interior, \
remodelación de espacios) o es arquitectura/urbanismo genérico sin foco en interiores?

Pesos para el score final (ya ponderado, vos sólo das los puntajes 0-10 por eje,
el score final lo calculamos nosotros): {weights}

Reglas:
- Si dos candidatos son la misma historia contada por dos medios distintos, quedate \
sólo con el mejor y marcá al otro como descartado por duplicado.
- Sé exigente: el objetivo es un feed de altísima señal, no cobertura exhaustiva.
- No inventes información que no esté en el candidato.

Formato de salida: SOLO un array JSON (sin texto alrededor), un objeto por candidato \
recibido (mismo "id"), con esta forma exacta:
{{"id": str, "scores": {{"novedad": num, "actualidad": num, "utilidad": num, \
"uso_materiales": num, "tendencia_industria": num, "encaje_tematico": num}}, \
"rationale": str (1-2 frases en español explicando la decisión)}}
"""


def _candidate_block(c: Candidate) -> str:
    return (
        f"id: {c.id}\n"
        f"origen: {c.origin}\n"
        f"fuente: {c.source_name}\n"
        f"título: {c.title}\n"
        f"fecha: {c.published_at or 'desconocida'}\n"
        f"resumen: {c.summary}\n"
        f"url: {c.url}\n"
    )


def curate(candidates: list[Candidate], cfg: Config) -> list[ScoredCandidate]:
    if not candidates:
        return []

    weights = cfg.rubric_weights
    system = SYSTEM_TEMPLATE.format(weights=weights)
    user = "Candidatos a evaluar:\n\n" + "\n---\n".join(_candidate_block(c) for c in candidates)

    raw = call_json(
        model=cfg.model("curator"),
        system=system,
        user=user,
        max_tokens=6000,
        temperature=0.2,
    )
    if not isinstance(raw, list):
        raise ValueError("El curador no devolvió una lista JSON")

    by_id = {c.id: c for c in candidates}
    scored: list[ScoredCandidate] = []
    for item in raw:
        cid = item.get("id")
        candidate = by_id.get(cid)
        if candidate is None:
            continue
        scores = {k: float(v) for k, v in item.get("scores", {}).items()}
        weighted = sum(scores.get(axis, 0.0) * w for axis, w in weights.items())
        scored.append(
            ScoredCandidate(
                candidate=candidate,
                scores=scores,
                weighted_score=round(weighted, 2),
                rationale=str(item.get("rationale", "")),
                selected=False,
            )
        )

    scored.sort(key=lambda s: s.weighted_score, reverse=True)

    selected_count = 0
    for s in scored:
        if selected_count >= cfg.max_selected_per_run:
            break
        if s.weighted_score >= cfg.min_score_to_select:
            s.selected = True
            selected_count += 1

    log.info(
        "Curador: %d candidatos evaluados, %d seleccionados (umbral %.1f)",
        len(scored),
        selected_count,
        cfg.min_score_to_select,
    )
    return scored
