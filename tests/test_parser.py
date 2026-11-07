import pytest

from matricula.core.errors import ParseError
from matricula.core.parser import parse_possibilidades


def test_reads_course_and_period(possibilidade_html: bytes) -> None:
    possibilidades = parse_possibilidades(possibilidade_html)

    assert possibilidades.curso == "CIÊNCIA DA COMPUTAÇÃO"
    assert possibilidades.habilitacao == "BACHARELADO EM CIÊNCIA DA COMPUTAÇÃO"
    assert possibilidades.periodo == "2026/2"


def test_reads_all_disciplines(possibilidade_html: bytes) -> None:
    possibilidades = parse_possibilidades(possibilidade_html)

    assert len(possibilidades.disciplinas) == 34
    assert sum(d.carater == "Obrigatória" for d in possibilidades.disciplinas) == 11
    assert sum(d.carater == "Eletiva" for d in possibilidades.disciplinas) == 23


def test_reads_discipline_fields(possibilidade_html: bytes) -> None:
    primeira = parse_possibilidades(possibilidade_html).disciplinas[0]

    assert primeira.sigla == "INF01113"
    assert primeira.nome == "ORGANIZAÇÃO DE COMPUTADORES"
    assert primeira.atividade_id == "3615"
    assert primeira.etapa == 4
    assert primeira.carater == "Obrigatória"
    assert primeira.creditos == 4
    assert primeira.ch_total == 60
    assert primeira.ch_extensao is None
    assert primeira.administrativa is False


def test_marks_administrative_disciplines(possibilidade_html: bytes) -> None:
    administrativas = [
        d
        for d in parse_possibilidades(possibilidade_html).disciplinas
        if d.administrativa
    ]

    assert {d.sigla for d in administrativas} == {
        "VAERE201",
        "VAERE202",
        "VAERE211",
        "VAERE212",
    }


def test_decodes_cp1252_accents(possibilidade_html: bytes) -> None:
    nomes = {d.nome for d in parse_possibilidades(possibilidade_html).disciplinas}

    assert "CÁLCULO NUMÉRICO A" in nomes
    assert "PROJETO E ANÁLISE DE ALGORITMOS II" in nomes


def test_rejects_html_without_table() -> None:
    with pytest.raises(ParseError, match="poss"):
        parse_possibilidades(b"<html><body>nada aqui</body></html>")
