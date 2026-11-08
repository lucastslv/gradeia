from types import SimpleNamespace

from matricula.ai.chat import MAX_STEPS, ChatService
from matricula.core.join import analyze
from matricula.core.models import Encontro, Turma
from matricula.core.parser import parse_possibilidades
from matricula.web.store import Mensagem


class FakeCompletions:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses) -> None:
        self.completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def content_response(text: str):
    message = SimpleNamespace(content=text, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def tool_response(name: str, arguments: str):
    call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name=name, arguments=arguments),
    )
    message = SimpleNamespace(content=None, tool_calls=[call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def analise(possibilidade_html: bytes):
    possibilidades = parse_possibilidades(possibilidade_html)
    turmas = [
        Turma(
            sigla="INF01113",
            nome="ORGANIZAÇÃO DE COMPUTADORES",
            turma="A",
            encontros=[Encontro(dia_semana=2, hora_inicio="08:30", hora_fim="10:10")],
        )
    ]
    return analyze(possibilidades, "305", 544, turmas)


def test_answers_without_tools(possibilidade_html: bytes) -> None:
    client = FakeClient([content_response("São 20 ofertadas.")])

    answer = ChatService(client, "deepseek-chat").reply(
        analise(possibilidade_html), [], "quantas estão ofertadas?"
    )

    assert answer == "São 20 ofertadas."
    assert client.completions.calls[0]["model"] == "deepseek-chat"
    messages = client.completions.calls[0]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[-1] == {"role": "user", "content": "quantas estão ofertadas?"}


def test_executes_tool_and_feeds_result_back(possibilidade_html: bytes) -> None:
    client = FakeClient(
        [
            tool_response("detalhar_disciplina", '{"sigla":"INF01113"}'),
            content_response("A turma A é segunda, 08:30–10:10."),
        ]
    )

    answer = ChatService(client, "deepseek-chat").reply(
        analise(possibilidade_html), [], "horário de INF01113?"
    )

    assert "turma A" in answer
    segunda_chamada = client.completions.calls[1]["messages"]
    resultados = [m for m in segunda_chamada if m["role"] == "tool"]
    assert resultados[0]["tool_call_id"] == "call_1"
    assert '"turma": "A"' in resultados[0]["content"]
    assert "ofertada" in resultados[0]["content"]


def test_sends_history_to_model(possibilidade_html: bytes) -> None:
    client = FakeClient([content_response("ok")])
    historico = [
        Mensagem(role="user", content="e as eletivas?"),
        Mensagem(role="assistant", content="são 23."),
    ]

    ChatService(client, "deepseek-chat").reply(
        analise(possibilidade_html), historico, "e as obrigatórias?"
    )

    messages = client.completions.calls[0]["messages"]
    assert {"role": "user", "content": "e as eletivas?"} in messages
    assert {"role": "assistant", "content": "são 23."} in messages


def test_stops_after_max_steps(possibilidade_html: bytes) -> None:
    client = FakeClient(
        [tool_response("resumo", "{}") for _ in range(MAX_STEPS)]
    )

    answer = ChatService(client, "deepseek-chat").reply(
        analise(possibilidade_html), [], "loop"
    )

    assert "Não consegui concluir" in answer
    assert len(client.completions.calls) == MAX_STEPS
