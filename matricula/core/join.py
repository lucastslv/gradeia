"""Junção entre as possibilidades do aluno e a oferta do período."""

from __future__ import annotations

from collections import defaultdict

from .models import (
    Analise,
    DisciplinaPossivel,
    Estado,
    OfertaDisciplina,
    Possibilidades,
    Resumo,
    Turma,
)


def analyze(
    possibilidades: Possibilidades,
    curso_id: str,
    period_total: int,
    turmas: list[Turma],
) -> Analise:
    """Cruza cada disciplina possível com as turmas ofertadas no período.

    Regra central: período sem nenhuma turma significa "ainda não publicado",
    nunca "nada é ofertado".
    """
    by_sigla: dict[str, list[Turma]] = defaultdict(list)
    for turma in turmas:
        by_sigla[turma.sigla].append(turma)

    publicado = period_total > 0
    ofertas = [
        _oferta(disciplina, by_sigla.get(disciplina.sigla, []), publicado)
        for disciplina in possibilidades.disciplinas
    ]

    return Analise(
        possibilidades=possibilidades,
        curso_id=curso_id,
        periodo_publicado=publicado,
        ofertas=ofertas,
        resumo=Resumo(
            total=len(ofertas),
            ofertadas=sum(o.estado is Estado.OFERTADA for o in ofertas),
            nao_ofertadas=sum(o.estado is Estado.NAO_OFERTADA for o in ofertas),
            nao_publicadas=sum(o.estado is Estado.NAO_PUBLICADO for o in ofertas),
        ),
    )


def _oferta(
    disciplina: DisciplinaPossivel,
    turmas: list[Turma],
    publicado: bool,
) -> OfertaDisciplina:
    if not publicado:
        return OfertaDisciplina(disciplina=disciplina, estado=Estado.NAO_PUBLICADO)
    if turmas:
        return OfertaDisciplina(
            disciplina=disciplina,
            estado=Estado.OFERTADA,
            turmas=sorted(turmas, key=lambda t: t.turma),
        )
    return OfertaDisciplina(disciplina=disciplina, estado=Estado.NAO_OFERTADA)
