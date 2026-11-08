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


def test_estado_da_grade_vazio(analise) -> None:
    assert AnalysisTools(analise).estado_da_grade() == {
        "total_disciplinas": 0,
        "total_creditos": 0,
        "selecionadas": [],
        "conflitos": [],
        "invalidas": [],
    }


def test_estado_da_grade_lista_escolhas(analise) -> None:
    resultado = AnalysisTools(
        analise, plano=[{"code": "INF01113", "letter": "A"}]
    ).estado_da_grade()

    assert resultado["total_disciplinas"] == 1
    assert resultado["total_creditos"] == 4
    assert resultado["selecionadas"][0]["sigla"] == "INF01113"
    assert resultado["selecionadas"][0]["turma"] == "A"
    assert resultado["conflitos"] == []
    assert resultado["invalidas"] == []


def test_estado_da_grade_marca_invalidas(analise) -> None:
    resultado = AnalysisTools(
        analise,
        plano=[
            {"code": "INF01090", "letter": "A"},
            {"code": "INF01113", "letter": "Z"},
        ],
    ).estado_da_grade()

    assert resultado["total_disciplinas"] == 0
    assert len(resultado["invalidas"]) == 2


def test_estado_da_grade_detecta_conflito(possibilidade_html: bytes) -> None:
    possibilidades = parse_possibilidades(possibilidade_html)
    turmas = [
        Turma(
            sigla="INF01113",
            nome="ORGANIZAÇÃO DE COMPUTADORES",
            turma="A",
            encontros=[
                Encontro(dia_semana=2, hora_inicio="08:30", hora_fim="10:10")
            ],
        ),
        Turma(
            sigla="INF05028",
            nome="PROJETO E ANÁLISE DE ALGORITMOS II",
            turma="A",
            encontros=[
                Encontro(dia_semana=2, hora_inicio="09:30", hora_fim="11:10")
            ],
        ),
    ]
    analise = analyze(possibilidades, "305", 544, turmas)

    resultado = AnalysisTools(
        analise,
        plano=[
            {"code": "INF01113", "letter": "A"},
            {"code": "INF05028", "letter": "A"},
        ],
    ).estado_da_grade()

    assert resultado["total_disciplinas"] == 2
    assert resultado["conflitos"] == [
        {
            "a": {"sigla": "INF01113", "turma": "A"},
            "b": {"sigla": "INF05028", "turma": "A"},
            "dia": "seg",
            "inicio": "09:30",
            "fim": "10:10",
        }
    ]


def test_call_estado_da_grade(analise) -> None:
    resultado = json.loads(
        AnalysisTools(analise, plano=[{"code": "INF01113", "letter": "A"}]).call(
            "estado_da_grade", "{}"
        )
    )

    assert resultado["total_disciplinas"] == 1


def turma(sigla: str, letter: str, inicio: str, fim: str, dia: int = 2) -> Turma:
    return Turma(
        sigla=sigla,
        nome=sigla,
        turma=letter,
        encontros=[
            Encontro(dia_semana=dia, hora_inicio=inicio, hora_fim=fim)
        ],
    )


def analise_dupla(possibilidade_html: bytes):
    possibilidades = parse_possibilidades(possibilidade_html)
    return analyze(
        possibilidades,
        "305",
        544,
        [
            turma("INF01113", "A", "08:30", "10:10"),
            turma("INF05028", "A", "09:30", "11:10"),
            turma("INF05028", "B", "13:30", "15:10"),
        ],
    )


def test_adicionar_disciplina_muta_plano(analise) -> None:
    plano: list[dict] = []
    tools = AnalysisTools(analise, plano=plano)

    resultado = tools.adicionar_disciplina("INF01113")

    assert resultado["ok"] is True
    assert resultado["turma"] == "A"
    assert plano == [{"code": "INF01113", "letter": "A"}]
    assert resultado["total_creditos"] == 4


def test_adicionar_disciplina_ja_na_grade(analise) -> None:
    tools = AnalysisTools(
        analise, plano=[{"code": "INF01113", "letter": "A"}]
    )

    resultado = tools.adicionar_disciplina("INF01113")

    assert resultado["ok"] is False
    assert "já está" in resultado["erro"]


def test_adicionar_disciplina_nao_ofertada(analise) -> None:
    resultado = AnalysisTools(analise, plano=[]).adicionar_disciplina("INF01090")

    assert resultado["ok"] is False
    assert "não está ofertada" in resultado["erro"]


def test_adicionar_disciplina_turma_inexistente(analise) -> None:
    resultado = AnalysisTools(analise, plano=[]).adicionar_disciplina(
        "INF01113", "Z"
    )

    assert resultado["ok"] is False
    assert "não encontrada" in resultado["erro"]


def test_adicionar_disciplina_escolhe_turma_sem_conflito(
    possibilidade_html: bytes,
) -> None:
    analise = analise_dupla(possibilidade_html)
    plano = [{"code": "INF01113", "letter": "A"}]
    tools = AnalysisTools(analise, plano=plano)

    resultado = tools.adicionar_disciplina("INF05028")

    assert resultado["ok"] is True
    assert resultado["turma"] == "B"
    assert plano[-1] == {"code": "INF05028", "letter": "B"}
    assert resultado["conflitos"] == []


def test_adicionar_disciplina_todas_conflitam(possibilidade_html: bytes) -> None:
    possibilidades = parse_possibilidades(possibilidade_html)
    analise = analyze(
        possibilidades,
        "305",
        544,
        [
            turma("INF01113", "A", "08:30", "10:10"),
            turma("INF05028", "A", "09:30", "11:10"),
        ],
    )
    tools = AnalysisTools(
        analise, plano=[{"code": "INF01113", "letter": "A"}]
    )

    resultado = tools.adicionar_disciplina("INF05028")

    assert resultado["ok"] is False
    assert "todas as turmas conflitam" in resultado["erro"]
    assert resultado["turmas"][0]["turma"] == "A"


def test_adicionar_disciplina_com_turma_conflitante(possibilidade_html: bytes) -> None:
    possibilidades = parse_possibilidades(possibilidade_html)
    analise = analyze(
        possibilidades,
        "305",
        544,
        [
            turma("INF01113", "A", "08:30", "10:10"),
            turma("INF05028", "A", "09:30", "11:10"),
        ],
    )
    tools = AnalysisTools(
        analise, plano=[{"code": "INF01113", "letter": "A"}]
    )

    resultado = tools.adicionar_disciplina("INF05028", "A")

    assert resultado["ok"] is True
    assert resultado["turma"] == "A"
    assert resultado["conflitos"]


def test_trocar_turma(possibilidade_html: bytes) -> None:
    analise = analise_dupla(possibilidade_html)
    plano = [
        {"code": "INF01113", "letter": "A"},
        {"code": "INF05028", "letter": "A"},
    ]
    tools = AnalysisTools(analise, plano=plano)

    resultado = tools.trocar_turma("INF05028", "B")

    assert resultado["ok"] is True
    assert resultado["turma"] == "B"
    assert plano[1] == {"code": "INF05028", "letter": "B"}
    assert resultado["conflitos"] == []


def test_trocar_turma_fora_da_grade(analise) -> None:
    resultado = AnalysisTools(analise, plano=[]).trocar_turma("INF01113", "A")

    assert resultado["ok"] is False
    assert "não está na grade" in resultado["erro"]


def test_remover_disciplina(analise) -> None:
    plano = [{"code": "INF01113", "letter": "A"}]
    tools = AnalysisTools(analise, plano=plano)

    resultado = tools.remover_disciplina("INF01113")

    assert resultado["ok"] is True
    assert plano == []
    assert resultado["total_creditos"] == 0

    novamente = tools.remover_disciplina("INF01113")
    assert novamente["ok"] is False


def test_call_escrita(analise) -> None:
    plano: list[dict] = []
    resultado = json.loads(
        AnalysisTools(analise, plano=plano).call(
            "adicionar_disciplina", '{"sigla":"INF01113"}'
        )
    )

    assert resultado["ok"] is True
    assert plano == [{"code": "INF01113", "letter": "A"}]


def analise_para_montar(possibilidade_html: bytes):
    possibilidades = parse_possibilidades(possibilidade_html)
    return analyze(
        possibilidades,
        "305",
        544,
        [
            turma("INF01113", "A", "08:30", "10:10"),
            turma("INF05028", "A", "09:30", "11:10"),
            turma("INF05028", "B", "08:30", "10:10", dia=3),
            turma("MAT01032", "U", "13:30", "15:10", dia=3),
            turma("INF01090", "N", "08:30", "10:10", dia=4),
        ],
    )


def test_montar_grade_prioriza_obrigatorias(possibilidade_html: bytes) -> None:
    analise = analise_para_montar(possibilidade_html)
    plano: list[dict] = []
    tools = AnalysisTools(analise, plano=plano)

    resultado = tools.montar_grade_sem_conflito(
        max_disciplinas=3, incluir_eletivas=False
    )

    assert resultado["ok"] is True
    assert resultado["total_disciplinas"] == 3
    assert resultado["conflitos"] == []
    assert [item["code"] for item in plano] == [
        "INF01113",
        "INF05028",
        "MAT01032",
    ]
    assert plano[1]["letter"] == "B"


def test_montar_grade_inclui_eletivas(possibilidade_html: bytes) -> None:
    analise = analise_para_montar(possibilidade_html)
    plano: list[dict] = []
    tools = AnalysisTools(analise, plano=plano)

    resultado = tools.montar_grade_sem_conflito(
        max_disciplinas=4, incluir_eletivas=True
    )

    assert resultado["total_disciplinas"] == 4
    assert any(item["code"] == "INF01090" for item in plano)


def test_montar_grade_respeita_limite(possibilidade_html: bytes) -> None:
    analise = analise_para_montar(possibilidade_html)
    plano: list[dict] = []
    tools = AnalysisTools(analise, plano=plano)

    tools.montar_grade_sem_conflito(max_disciplinas=2)

    assert len(plano) == 2


def test_montar_grade_parte_do_plano_atual(possibilidade_html: bytes) -> None:
    analise = analise_para_montar(possibilidade_html)
    plano = [{"code": "INF01113", "letter": "A"}]
    tools = AnalysisTools(analise, plano=plano)

    resultado = tools.montar_grade_sem_conflito(max_disciplinas=3)

    assert resultado["total_disciplinas"] == 3
    assert resultado["conflitos"] == []
    assert len(plano) == 3


def test_call_montar_grade(possibilidade_html: bytes) -> None:
    analise = analise_para_montar(possibilidade_html)
    plano: list[dict] = []
    resultado = json.loads(
        AnalysisTools(analise, plano=plano).call(
            "montar_grade_sem_conflito", '{"max_disciplinas":2}'
        )
    )

    assert resultado["total_disciplinas"] == 2
    assert len(plano) == 2
