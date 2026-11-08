from types import SimpleNamespace

from matricula.ai.chat import MAX_STEPS, ChatService
from matricula.core.join import analyze
from matricula.core.models import Encontro, Turma
from matricula.core.parser import parse_possibilidades
from matricula.web.store import Mensagem


class FakeResponses:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses) -> None:
        self.responses = FakeResponses(responses)


def content_response(text: str):
    item = SimpleNamespace(
        type="message",
        id="msg_1",
        role="assistant",
        content=[SimpleNamespace(type="output_text", text=text)],
    )
    return SimpleNamespace(output=[item], output_text=text)


def tool_response(name: str, arguments: str):
    item = SimpleNamespace(
        type="function_call",
        id="fc_1",
        call_id="call_1",
        name=name,
        arguments=arguments,
    )
    return SimpleNamespace(output=[item], output_text="")


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

    answer = ChatService(client, "deepseek-flash").reply(
        analise(possibilidade_html), [], "quantas estão ofertadas?"
    )

    assert answer == "São 20 ofertadas."
    chamada = client.responses.calls[0]
    assert chamada["model"] == "deepseek-flash"
    assert chamada["reasoning"] == {"effort": "none"}
    assert chamada["tool_choice"] == "auto"
    assert "CIÊNCIA DA COMPUTAÇÃO" in chamada["instructions"]
    assert chamada["input"] == [
        {"role": "user", "content": "quantas estão ofertadas?"}
    ]


def test_tool_schemas_use_responses_format(possibilidade_html: bytes) -> None:
    client = FakeClient([content_response("ok")])

    ChatService(client, "deepseek-flash").reply(
        analise(possibilidade_html), [], "oi"
    )

    ferramenta = client.responses.calls[0]["tools"][0]
    assert ferramenta["type"] == "function"
    assert ferramenta["name"] == "resumo"
    assert "parameters" in ferramenta
    assert "function" not in ferramenta


def test_executes_tool_and_feeds_result_back(possibilidade_html: bytes) -> None:
    client = FakeClient(
        [
            tool_response("detalhar_disciplina", '{"sigla":"INF01113"}'),
            content_response("A turma A é segunda, 08:30–10:10."),
        ]
    )

    answer = ChatService(client, "deepseek-flash").reply(
        analise(possibilidade_html), [], "horário de INF01113?"
    )

    assert "turma A" in answer
    segunda_chamada = client.responses.calls[1]["input"]
    saidas = [
        item
        for item in segunda_chamada
        if item.get("type") == "function_call_output"
    ]
    assert saidas[0]["call_id"] == "call_1"
    assert '"turma": "A"' in saidas[0]["output"]
    assert "ofertada" in saidas[0]["output"]
    assert any(item.get("type") == "function_call" for item in segunda_chamada)


def test_replays_reasoning_items(possibilidade_html: bytes) -> None:
    reasoning = SimpleNamespace(
        type="reasoning",
        id="rs_1",
        content=[SimpleNamespace(type="reasoning_text", text="vou consultar")],
    )
    call = SimpleNamespace(
        type="function_call",
        id="fc_1",
        call_id="call_1",
        name="resumo",
        arguments="{}",
    )
    client = FakeClient(
        [SimpleNamespace(output=[reasoning, call], output_text=""), content_response("ok")]
    )

    ChatService(client, "deepseek-flash").reply(
        analise(possibilidade_html), [], "resuma"
    )

    segunda_chamada = client.responses.calls[1]["input"]
    raciocinio = [item for item in segunda_chamada if item.get("type") == "reasoning"]
    assert raciocinio[0]["content"][0]["text"] == "vou consultar"


def test_sends_history_to_model(possibilidade_html: bytes) -> None:
    client = FakeClient([content_response("ok")])
    historico = [
        Mensagem(role="user", content="e as eletivas?"),
        Mensagem(role="assistant", content="são 23."),
    ]

    ChatService(client, "deepseek-flash").reply(
        analise(possibilidade_html), historico, "e as obrigatórias?"
    )

    entrada = client.responses.calls[0]["input"]
    assert {"role": "user", "content": "e as eletivas?"} in entrada
    assert {"role": "assistant", "content": "são 23."} in entrada
    assert entrada[-1] == {"role": "user", "content": "e as obrigatórias?"}


def test_stops_after_max_steps(possibilidade_html: bytes) -> None:
    client = FakeClient(
        [tool_response("resumo", "{}") for _ in range(MAX_STEPS)]
    )

    answer = ChatService(client, "deepseek-flash").reply(
        analise(possibilidade_html), [], "loop"
    )

    assert "Não consegui concluir" in answer
    assert len(client.responses.calls) == MAX_STEPS
