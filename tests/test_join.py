from matricula.core.join import analyze
from matricula.core.models import (
    DisciplinaPossivel,
    Estado,
    Possibilidades,
    Turma,
)


def disciplina(sigla: str, etapa: int | None = 4) -> DisciplinaPossivel:
    return DisciplinaPossivel(
        sigla=sigla,
        nome=f"DISCIPLINA {sigla}",
        etapa=etapa,
        carater="Obrigatória",
        creditos=4,
        ch_total=60,
    )


def possibilidades(*siglas: str) -> Possibilidades:
    return Possibilidades(
        curso="CIÊNCIA DA COMPUTAÇÃO",
        periodo="2026/2",
        disciplinas=[disciplina(sigla) for sigla in siglas],
    )


def turma(sigla: str) -> Turma:
    return Turma(sigla=sigla, nome=f"DISCIPLINA {sigla}", turma="A")


def test_marks_disciplines_with_classes_as_offered() -> None:
    analise = analyze(
        possibilidades("INF01113", "INF01090"),
        curso_id="305",
        period_total=544,
        turmas=[turma("INF01113")],
    )

    estados = {o.disciplina.sigla: o.estado for o in analise.ofertas}

    assert estados["INF01113"] is Estado.OFERTADA
    assert estados["INF01090"] is Estado.NAO_OFERTADA
    assert analise.resumo.ofertadas == 1
    assert analise.resumo.nao_ofertadas == 1
    assert analise.resumo.nao_publicadas == 0


def test_empty_period_marks_everything_as_not_published() -> None:
    analise = analyze(
        possibilidades("INF01113", "INF01090"),
        curso_id="305",
        period_total=0,
        turmas=[],
    )

    assert all(o.estado is Estado.NAO_PUBLICADO for o in analise.ofertas)
    assert all(not o.turmas for o in analise.ofertas)
    assert analise.periodo_publicado is False
    assert analise.resumo.nao_publicadas == 2
    assert analise.resumo.nao_ofertadas == 0


def test_keeps_possibility_order() -> None:
    analise = analyze(
        possibilidades("INF05028", "INF01113"),
        curso_id="305",
        period_total=1,
        turmas=[],
    )

    assert [o.disciplina.sigla for o in analise.ofertas] == ["INF05028", "INF01113"]
