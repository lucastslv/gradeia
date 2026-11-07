from matricula.core.models import Turma
from matricula.service.possibilidades import analisar_html


class FakeApi:
    def __init__(self, total: int, siglas: list[str]) -> None:
        self.total = total
        self.siglas = siglas

    def resolve_curso(self, nome: str, grau: str | None = None) -> str:
        assert nome == "CIÊNCIA DA COMPUTAÇÃO"
        return "305"

    def period_total(self, periodo: str) -> int:
        assert periodo == "2026/2"
        return self.total

    def list_turmas(self, periodo: str, curso_id: str) -> list[Turma]:
        assert curso_id == "305"
        return [
            Turma(sigla=sigla, nome=sigla, turma="A") for sigla in self.siglas
        ]


def test_uses_file_period_and_course(possibilidade_html: bytes) -> None:
    analise = analisar_html(possibilidade_html, FakeApi(544, ["INF01113"]))

    assert analise.possibilidades.periodo == "2026/2"
    assert analise.curso_id == "305"
    assert analise.resumo.total == 34
    assert analise.resumo.ofertadas == 1
    assert analise.resumo.nao_ofertadas == 33


def test_skips_class_lookup_when_period_is_not_published(
    possibilidade_html: bytes,
) -> None:
    api = FakeApi(0, [])
    api.list_turmas = lambda periodo, curso_id: (_ for _ in ()).throw(
        AssertionError("não deveria buscar turmas de período não publicado")
    )

    analise = analisar_html(possibilidade_html, api)

    assert analise.resumo.nao_publicadas == 34
