import json

import pytest

from matricula.ai.tools import AnalysisTools
from matricula.core.join import analyze
from matricula.core.models import Encontro, Turma
from matricula.core.parser import parse_possibilidades


@pytest.fixture
def analise(possibilidade_html: bytes):
    possibilidades = parse_possibilidades(possibilidade_html)
    turmas = [
        Turma(
            sigla="INF01113",
            nome="ORGANIZAÇÃO DE COMPUTADORES",
            turma="A",
            encontros=[
                Encontro(
                    dia_semana=2,
                    hora_inicio="08:30",
                    hora_fim="10:10",
                    campus="Vale",
                )
            ],
        )
    ]
    return analyze(possibilidades, "305", 544, turmas)


def test_resumo(analise) -> None:
    assert AnalysisTools(analise).resumo() == {
        "curso": "CIÊNCIA DA COMPUTAÇÃO",
        "periodo": "2026/2",
        "periodo_publicado": True,
        "total": 34,
        "ofertadas": 1,
        "nao_ofertadas": 33,
        "nao_publicadas": 0,
    }


def test_lista_apenas_ofertadas(analise) -> None:
    resultado = AnalysisTools(analise).listar_disciplinas(estado="ofertada")

    assert resultado["total"] == 1
    assert resultado["itens"][0]["sigla"] == "INF01113"


def test_lista_eletivas_com_busca(analise) -> None:
    resultado = AnalysisTools(analise).listar_disciplinas(
        carater="Eletiva", busca="cálculo"
    )

    assert resultado["total"] == 0

    resultado = AnalysisTools(analise).listar_disciplinas(
        carater="Eletiva", busca="ciência de dados"
    )
    assert [item["sigla"] for item in resultado["itens"]] == ["INF01090"]


def test_detalha_disciplina_com_turmas(analise) -> None:
    detalhe = AnalysisTools(analise).detalhar_disciplina("inf01113")

    assert detalhe["estado"] == "ofertada"
    assert detalhe["turmas"][0]["turma"] == "A"
    assert detalhe["turmas"][0]["encontros"][0]["dia"] == "seg"
    assert detalhe["turmas"][0]["campus"] == "Vale"


def test_detalha_disciplina_nao_ofertada(analise) -> None:
    detalhe = AnalysisTools(analise).detalhar_disciplina("INF01090")

    assert detalhe["estado"] == "nao_ofertada"
    assert detalhe["turmas"] == []


def test_sigla_desconhecida(analise) -> None:
    assert "erro" in AnalysisTools(analise).detalhar_disciplina("XXX0000")


def test_call_serializa_resultado(analise) -> None:
    resultado = json.loads(AnalysisTools(analise).call("resumo", None))

    assert resultado["total"] == 34


def test_call_rejeita_ferramenta_e_argumentos_invalidos(analise) -> None:
    tools = AnalysisTools(analise)

    assert "erro" in json.loads(tools.call("inexistente", "{}"))
    assert "erro" in json.loads(tools.call("listar_disciplinas", "{quebrado"))
    assert "erro" in json.loads(tools.call("listar_disciplinas", "[]"))
    assert "erro" in json.loads(tools.call("listar_disciplinas", '{"estado":"x"}'))
