from matricula.core.join import analyze
from matricula.core.models import Encontro, Turma
from matricula.core.parser import parse_possibilidades
from matricula.web.planner import planner_payload


def build_analise(possibilidade_html: bytes):
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
                    espaco="SALA 113",
                ),
                Encontro(
                    dia_semana=4,
                    hora_inicio="08:30",
                    hora_fim="10:10",
                    campus="Vale",
                    espaco="SALA 113",
                ),
            ],
        )
    ]
    return analyze(possibilidades, "305", 544, turmas)


def test_payload_has_all_courses_and_plan(possibilidade_html: bytes) -> None:
    analise = build_analise(possibilidade_html)

    payload = planner_payload(
        analise, "abc123", [{"code": "INF01113", "letter": "A"}]
    )

    assert payload["analise_id"] == "abc123"
    assert payload["periodo"] == "2026/2"
    assert payload["periodo_publicado"] is True
    assert len(payload["cursos"]) == 34
    assert payload["plano"] == [{"code": "INF01113", "letter": "A"}]


def test_payload_maps_sessions_to_grid_days(possibilidade_html: bytes) -> None:
    payload = planner_payload(build_analise(possibilidade_html), "x", [])

    curso = next(c for c in payload["cursos"] if c["code"] == "INF01113")
    turma = curso["turmas"][0]

    assert curso["estado"] == "ofertada"
    assert curso["carater"] == "Obrigatória"
    assert turma["letter"] == "A"
    assert turma["campus"] == "Vale"
    assert turma["local"] == "SALA 113"
    assert turma["sessions"] == [
        {"day": 0, "start": 510, "end": 610},
        {"day": 2, "start": 510, "end": 610},
    ]


def test_payload_keeps_not_offered_courses(possibilidade_html: bytes) -> None:
    payload = planner_payload(build_analise(possibilidade_html), "x", [])

    curso = next(c for c in payload["cursos"] if c["code"] == "INF01090")

    assert curso["estado"] == "nao_ofertada"
    assert curso["turmas"] == []
