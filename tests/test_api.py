import httpx
import pytest

from matricula.core.api import CURSOS_PATH, TURMAS_PATH, UfrgsApi
from matricula.core.cache import NullCache
from matricula.core.errors import AmbiguousCourse, ApiError, CourseNotFound


def make_api(handler) -> UfrgsApi:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return UfrgsApi(client=client, cache=NullCache())


def envelope(**data):
    return {"success": True, "code": 200, "message": "OK", "data": data}


def curso(identificador: str, nome: str, grau: str = "BACHARELADO"):
    return {"Identificador": identificador, "Curso": nome, "Grau": grau}


def test_paginates_and_dedupes_courses() -> None:
    pages = {
        1: envelope(
            items=[curso("305", "CIÊNCIA DA COMPUTAÇÃO")],
            _meta={"pageCount": 2},
        ),
        2: envelope(
            items=[
                curso("305", "CIÊNCIA DA COMPUTAÇÃO"),
                curso("305", "CIÊNCIA DA COMPUTAÇÃO", "TECNÓLOGO"),
                curso("318", "ENGENHARIA DE COMPUTAÇÃO"),
            ],
            _meta={"pageCount": 2},
        ),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == CURSOS_PATH
        return httpx.Response(200, json=pages[int(request.url.params["page"])])

    cursos = make_api(handler).list_cursos()

    assert len(cursos) == 3
    assert {c["Identificador"] for c in cursos} == {"305", "318"}


def test_resolves_course_by_name_and_degree() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=envelope(
                items=[
                    curso("305", "CIÊNCIA DA COMPUTAÇÃO"),
                    curso("305", "CIÊNCIA DA COMPUTAÇÃO", "TECNÓLOGO"),
                    curso("318", "ENGENHARIA DE COMPUTAÇÃO"),
                ],
                _meta={"pageCount": 1},
            ),
        )

    api = make_api(handler)

    assert api.resolve_curso("Ciência da Computação") == "305"
    assert (
        api.resolve_curso(
            "CIÊNCIA DA COMPUTAÇÃO", "BACHARELADO EM CIÊNCIA DA COMPUTAÇÃO"
        )
        == "305"
    )


def test_raises_on_unknown_course() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=envelope(items=[curso("318", "ENGENHARIA")], _meta={"pageCount": 1}),
        )

    with pytest.raises(CourseNotFound):
        make_api(handler).resolve_curso("MEDICINA")


def test_raises_on_ambiguous_course() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=envelope(
                items=[curso("1", "FÍSICA"), curso("2", "FÍSICA")],
                _meta={"pageCount": 1},
            ),
        )

    with pytest.raises(AmbiguousCourse):
        make_api(handler).resolve_curso("FÍSICA")


def test_groups_classes_by_sigla_and_turma() -> None:
    rows = [
        {
            "Sigla": "INF01113",
            "NomeAtividadeEnsino": "ORGANIZAÇÃO DE COMPUTADORES B",
            "Turma": "A ",
            "DiaSemana": "2",
            "HoraInicio": "08:30",
            "HoraFim": "10:10",
            "DenominacaoCampus": "Vale",
        },
        {
            "Sigla": "INF01113",
            "NomeAtividadeEnsino": "ORGANIZAÇÃO DE COMPUTADORES B",
            "Turma": "A ",
            "DiaSemana": "4",
            "HoraInicio": "08:30",
            "HoraFim": "10:10",
            "DenominacaoCampus": "Vale",
        },
        {
            "Sigla": "INF01113",
            "NomeAtividadeEnsino": "ORGANIZAÇÃO DE COMPUTADORES B",
            "Turma": "B ",
            "DiaSemana": "5",
            "HoraInicio": "10:30",
            "HoraFim": "12:10",
            "DenominacaoCampus": "Vale",
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == TURMAS_PATH
        assert request.url.params["periodo"] == "2026/2"
        assert request.url.params["curso"] == "305"
        return httpx.Response(
            200, json=envelope(turmas=rows, _meta={"pageCount": 1})
        )

    turmas = make_api(handler).list_turmas("2026/2", "305")

    assert [t.turma for t in turmas] == ["A", "B"]
    assert len(turmas[0].encontros) == 2
    assert turmas[0].encontros[0].dia_semana == 2
    assert turmas[0].encontros[0].campus == "Vale"


def test_period_total_zero_means_not_published() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=envelope(turmas=[], _meta={"totalCount": 0})
        )

    assert make_api(handler).period_total("2027/1") == 0


def test_api_errors_are_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with pytest.raises(ApiError):
        make_api(handler).period_total("2026/2")

    def unsuccessful(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": False, "data": {}})

    with pytest.raises(ApiError):
        make_api(unsuccessful).period_total("2026/2")
