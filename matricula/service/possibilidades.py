"""Caso de uso: verificar a oferta do período para um HTML de possibilidades."""

from __future__ import annotations

from ..core.api import UfrgsApi
from ..core.join import analyze
from ..core.models import Analise
from ..core.parser import parse_possibilidades


def analisar_html(raw: bytes, api: UfrgsApi) -> Analise:
    possibilidades = parse_possibilidades(raw)
    curso_id = api.resolve_curso(possibilidades.curso, possibilidades.habilitacao)

    period_total = api.period_total(possibilidades.periodo)
    turmas = (
        api.list_turmas(possibilidades.periodo, curso_id) if period_total > 0 else []
    )
    return analyze(possibilidades, curso_id, period_total, turmas)
