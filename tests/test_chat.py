import asyncio
from types import SimpleNamespace

from matricula.ai.chat import MAX_STEPS, ChatService
from matricula.core.join import analyze
from matricula.core.models import Encontro, Turma
from matricula.core.parser import parse_possibilidades
from matricula.web.store import Mensagem


class FakeStream:
    def __init__(self, events) -> None:
        self._events = iter(events)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._events)
        except StopIteration:
            raise StopAsyncIteration


class FakeAsyncResponses:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if kwargs.get("stream"):
            return FakeStream(item)
        return item


class FakeClient:
    def __init__(self, responses) -> None:
        self.responses = FakeAsyncResponses(responses)


def message_item(text: str):
    return SimpleNamespace(
        type="message",
        id="msg_1",
        role="assistant",
        content=[SimpleNamespace(type="output_text", text=text)],
    )


def content_response(text: str):
    return SimpleNamespace(output=[message_item(text)], output_text=text)


def tool_response(name: str, arguments: str):
    item = SimpleNamespace(
        type="function_call",
        id="fc_1",
        call_id="call_1",
        name=name,
        arguments=arguments,
    )
    return SimpleNamespace(output=[item], output_text="")


def delta(text: str):
    return SimpleNamespace(type="response.output_text.delta", delta=text)


def completed(output, text: str = ""):
    response = SimpleNamespace(output=output, output_text=text)
    return SimpleNamespace(type="response.completed", response=response)


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
    service = ChatService(client, "deepseek-flash")

    answer = asyncio.run(
        service.reply(analise(possibilidade_html), [], "quantas estão ofertadas?")
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
    asyncio.run(
        ChatService(client, "deepseek-flash").reply(
            analise(possibilidade_html), [], "oi"
        )
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

    answer = asyncio.run(
        ChatService(client, "deepseek-flash").reply(
            analise(possibilidade_html), [], "horário de INF01113?"
        )
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
        [
            SimpleNamespace(output=[reasoning, call], output_text=""),
            content_response("ok"),
        ]
    )

    asyncio.run(
        ChatService(client, "deepseek-flash").reply(
            analise(possibilidade_html), [], "resuma"
        )
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

    asyncio.run(
        ChatService(client, "deepseek-flash").reply(
            analise(possibilidade_html), historico, "e as obrigatórias?"
        )
    )

    entrada = client.responses.calls[0]["input"]
    assert {"role": "user", "content": "e as eletivas?"} in entrada
    assert {"role": "assistant", "content": "são 23."} in entrada
    assert entrada[-1] == {"role": "user", "content": "e as obrigatórias?"}


def test_stops_after_max_steps(possibilidade_html: bytes) -> None:
    client = FakeClient([tool_response("resumo", "{}") for _ in range(MAX_STEPS)])

    answer = asyncio.run(
        ChatService(client, "deepseek-flash").reply(
            analise(possibilidade_html), [], "loop"
        )
    )

    assert "Não consegui concluir" in answer
    assert len(client.responses.calls) == MAX_STEPS


def test_tool_reads_current_plan(possibilidade_html: bytes) -> None:
    client = FakeClient(
        [
            tool_response("estado_da_grade", "{}"),
            content_response("Sua grade tem 1 disciplina."),
        ]
    )

    answer = asyncio.run(
        ChatService(client, "deepseek-flash").reply(
            analise(possibilidade_html),
            [],
            "minha grade?",
            plano=[{"code": "INF01113", "letter": "A"}],
        )
    )

    assert "1 disciplina" in answer
    segunda_chamada = client.responses.calls[1]["input"]
    saidas = [
        item
        for item in segunda_chamada
        if item.get("type") == "function_call_output"
    ]
    assert "INF01113" in saidas[0]["output"]
    assert '"turma": "A"' in saidas[0]["output"]


def test_stream_emits_plan_event(possibilidade_html: bytes) -> None:
    chamada = SimpleNamespace(
        type="function_call",
        id="fc_1",
        call_id="call_1",
        name="adicionar_disciplina",
        arguments='{"sigla":"INF01113"}',
    )
    client = FakeClient(
        [
            [completed([chamada], "")],
            [completed([message_item("Adicionei.")], "Adicionei.")],
        ]
    )
    plano: list[dict] = []

    eventos = asyncio.run(
        collect_stream(
            client,
            analise(possibilidade_html),
            pergunta="adicione INF01113",
            plano=plano,
        )
    )

    planos = [evento for evento in eventos if evento["type"] == "plano"]
    assert planos[0]["plano"] == [{"code": "INF01113", "letter": "A"}]
    assert plano == [{"code": "INF01113", "letter": "A"}]
    assert eventos[-1] == {"type": "done", "text": "Adicionei."}


def test_reply_mutates_plan(possibilidade_html: bytes) -> None:
    client = FakeClient(
        [
            tool_response("adicionar_disciplina", '{"sigla":"INF01113"}'),
            content_response("ok"),
        ]
    )
    plano: list[dict] = []

    answer = asyncio.run(
        ChatService(client, "deepseek-flash").reply(
            analise(possibilidade_html), [], "adicione", plano=plano
        )
    )

    assert answer == "ok"
    assert plano == [{"code": "INF01113", "letter": "A"}]


async def collect_stream(client, analise_, history=None, pergunta="oi", plano=None):
    service = ChatService(client, "deepseek-flash")
    return [
        evento
        async for evento in service.stream_reply(
            analise_, history or [], pergunta, plano=plano
        )
    ]


def test_streams_text_and_done(possibilidade_html: bytes) -> None:
    client = FakeClient(
        [
            [
                delta("Olá"),
                delta(", mundo"),
                completed([message_item("Olá, mundo")], "Olá, mundo"),
            ]
        ]
    )

    eventos = asyncio.run(collect_stream(client, analise(possibilidade_html)))

    assert eventos == [
        {"type": "delta", "text": "Olá"},
        {"type": "delta", "text": ", mundo"},
        {"type": "done", "text": "Olá, mundo"},
    ]
    assert client.responses.calls[0]["stream"] is True


def test_stream_resets_between_tool_rounds(possibilidade_html: bytes) -> None:
    chamada = SimpleNamespace(
        type="function_call",
        id="fc_1",
        call_id="call_1",
        name="detalhar_disciplina",
        arguments='{"sigla":"INF01113"}',
    )
    client = FakeClient(
        [
            [delta("Vou consultar"), completed([chamada], "")],
            [delta("A turma A"), completed([message_item("A turma A")], "A turma A")],
        ]
    )

    eventos = asyncio.run(
        collect_stream(client, analise(possibilidade_html), pergunta="horário?")
    )

    assert {"type": "reset"} in eventos
    assert eventos[-1] == {"type": "done", "text": "A turma A"}
    segunda_chamada = client.responses.calls[1]["input"]
    assert any(item.get("type") == "function_call_output" for item in segunda_chamada)


def test_stream_emits_error_when_failed(possibilidade_html: bytes) -> None:
    failed = SimpleNamespace(
        type="response.failed",
        response=SimpleNamespace(output=[], output_text=""),
    )
    client = FakeClient([[failed]])

    eventos = asyncio.run(collect_stream(client, analise(possibilidade_html)))

    assert eventos == [{"type": "error", "text": "Não consegui concluir a resposta."}]
