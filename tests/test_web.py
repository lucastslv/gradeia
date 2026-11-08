import pytest
from fastapi.testclient import TestClient

from matricula.core.models import Encontro, Turma
from matricula.web.app import app, get_api, get_chat_service, get_store
from matricula.web.store import AnalysisStore


class FakeApi:
    def __init__(self, total: int = 544) -> None:
        self.total = total

    def resolve_curso(self, nome: str, grau: str | None = None) -> str:
        assert nome == "CIÊNCIA DA COMPUTAÇÃO"
        return "305"

    def period_total(self, periodo: str) -> int:
        return self.total

    def list_turmas(self, periodo: str, curso_id: str) -> list[Turma]:
        if self.total == 0:
            return []
        return [
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


class FakeChatService:
    def reply(self, analise, history, pergunta: str) -> str:
        return f"**resposta** para: {pergunta}"


@pytest.fixture
def client(tmp_path):
    store = AnalysisStore(tmp_path / "analises.db")
    app.dependency_overrides[get_api] = lambda: FakeApi()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def upload(client: TestClient, html: bytes):
    return client.post(
        "/analisar",
        files={"arquivo": ("possibilidade.html", html, "text/html")},
        follow_redirects=True,
    )


def analise_id(response) -> str:
    return str(response.url).rstrip("/").rsplit("/", 1)[-1]


def test_index_has_upload_form(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Possibilidade de Matrícula" in response.text


def test_upload_renders_report(client: TestClient, possibilidade_html: bytes) -> None:
    response = upload(client, possibilidade_html)

    assert response.status_code == 200
    assert "CIÊNCIA DA COMPUTAÇÃO" in response.text
    assert "Período 2026/2" in response.text
    assert "INF01113" in response.text


def test_filter_by_offered(client: TestClient, possibilidade_html: bytes) -> None:
    response = upload(client, possibilidade_html)

    linhas = client.get(f"/analise/{analise_id(response)}/linhas?estado=ofertada")

    assert "INF01113" in linhas.text
    assert "INF01090" not in linhas.text


def test_filter_by_elective(client: TestClient, possibilidade_html: bytes) -> None:
    response = upload(client, possibilidade_html)

    linhas = client.get(f"/analise/{analise_id(response)}/linhas?carater=eletiva")

    assert "INF01090" in linhas.text
    assert "INF01113" not in linhas.text


def test_search_by_sigla(client: TestClient, possibilidade_html: bytes) -> None:
    response = upload(client, possibilidade_html)

    linhas = client.get(f"/analise/{analise_id(response)}/linhas?q=inf01113")

    assert "INF01113" in linhas.text
    assert "INF01090" not in linhas.text


def test_reverificar_redirects(client: TestClient, possibilidade_html: bytes) -> None:
    response = upload(client, possibilidade_html)
    ident = analise_id(response)

    nova = client.post(f"/analise/{ident}/reverificar", follow_redirects=True)

    assert nova.status_code == 200
    assert "CIÊNCIA DA COMPUTAÇÃO" in nova.text


def test_unpublished_period_shows_warning(tmp_path, possibilidade_html: bytes) -> None:
    store = AnalysisStore(tmp_path / "analises.db")
    app.dependency_overrides[get_api] = lambda: FakeApi(total=0)
    app.dependency_overrides[get_store] = lambda: store

    with TestClient(app) as test_client:
        response = upload(test_client, possibilidade_html)
        assert test_client.get("/").status_code == 200

    app.dependency_overrides.clear()

    assert "ainda não foi publicada" in response.text


def test_rejects_html_without_table(client: TestClient) -> None:
    response = client.post(
        "/analisar",
        files={"arquivo": ("x.html", b"<html><body>nada</body></html>", "text/html")},
    )

    assert response.status_code == 400
    assert "tabela" in response.text


def test_rejects_empty_file(client: TestClient) -> None:
    response = client.post(
        "/analisar", files={"arquivo": ("x.html", b"", "text/html")}
    )

    assert response.status_code == 400


def test_unknown_analysis_returns_404(client: TestClient) -> None:
    assert client.get("/analise/inexistente").status_code == 404


def test_chat_renders_markdown_and_keeps_history(
    client: TestClient, possibilidade_html: bytes
) -> None:
    response = upload(client, possibilidade_html)
    ident = analise_id(response)

    primeira = client.post(
        f"/analise/{ident}/chat", data={"mensagem": "quais obrigatórias?"}
    )

    assert primeira.status_code == 200
    assert "<strong>resposta</strong>" in primeira.text
    assert "para: quais obrigatórias?" in primeira.text

    segunda = client.post(f"/analise/{ident}/chat", data={"mensagem": "e as eletivas?"})

    assert "para: quais obrigatórias?" in segunda.text
    assert "para: e as eletivas?" in segunda.text


def test_chat_without_api_key_shows_notice(
    tmp_path, possibilidade_html: bytes
) -> None:
    store = AnalysisStore(tmp_path / "analises.db")
    app.dependency_overrides[get_api] = lambda: FakeApi()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_chat_service] = lambda: None

    with TestClient(app) as test_client:
        response = upload(test_client, possibilidade_html)
        ident = analise_id(response)
        chat = test_client.post(
            f"/analise/{ident}/chat", data={"mensagem": "oi"}
        )

    app.dependency_overrides.clear()

    assert "Defina <code>DEEPSEEK_API_KEY</code>" in response.text
    assert "não está configurado" in chat.text
