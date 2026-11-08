"""Serialização da análise no formato consumido pela ilha Svelte."""

from __future__ import annotations

from typing import Any

from ..core.models import Analise, OfertaDisciplina, Turma

# A API usa DiaSemana 2..7 (2=segunda); a grade usa 0..5 (0=segunda).
DAY_OFFSET = 2


def planner_payload(
    analise: Analise, analise_id: str, plano: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "analise_id": analise_id,
        "curso": analise.possibilidades.curso,
        "periodo": analise.possibilidades.periodo,
        "periodo_publicado": analise.periodo_publicado,
        "cursos": [_curso(oferta) for oferta in analise.ofertas],
        "plano": plano,
    }


def _curso(oferta: OfertaDisciplina) -> dict[str, Any]:
    disciplina = oferta.disciplina
    return {
        "code": disciplina.sigla,
        "name": disciplina.nome,
        "credits": disciplina.creditos,
        "estado": oferta.estado.value,
        "carater": disciplina.carater,
        "etapa": disciplina.etapa,
        "turmas": [_turma(turma) for turma in oferta.turmas],
    }


def _turma(turma: Turma) -> dict[str, Any]:
    sessions = []
    campus = None
    local = None

    for encontro in turma.encontros:
        if encontro.dia_semana is None:
            continue
        day = encontro.dia_semana - DAY_OFFSET
        start = _minutes(encontro.hora_inicio)
        end = _minutes(encontro.hora_fim)
        if day < 0 or day > 5 or start is None or end is None or end <= start:
            continue
        sessions.append({"day": day, "start": start, "end": end})
        campus = campus or encontro.campus
        local = local or encontro.espaco

    return {
        "letter": turma.turma,
        "sessions": sessions,
        "campus": campus,
        "local": local,
    }


def _minutes(value: str | None) -> int | None:
    if not value:
        return None
    try:
        hour, minute = value.split(":")[:2]
        return int(hour) * 60 + int(minute)
    except (ValueError, AttributeError):
        return None
