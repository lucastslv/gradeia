import asyncio
import json

import httpx
from openai import AsyncOpenAI

from matricula.ai.chat import ChatService
from matricula.core.join import analyze
from matricula.core.models import DisciplinaPossivel, Possibilidades


def analise_minima():
    possibilidades = Possibilidades(
        curso="CIÊNCIA DA COMPUTAÇÃO",
        periodo="2026/2",
        disciplinas=[
            DisciplinaPossivel(
                sigla="INF01113",
                nome="ORGANIZAÇÃO DE COMPUTADORES",
                etapa=4,
                carater="Obrigatória",
                creditos=4,
                ch_total=60,
            )
        ],
    )
    return analyze(possibilidades, "305", 1, [])


def test_sdk_sends_responses_payload() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "resp_1",
                "object": "response",
                "created_at": 0,
                "status": "completed",
                "model": "deepseek-flash",
                "output": [
                    {
                        "type": "message",
                        "id": "msg_1",
                        "status": "completed",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "ok"}],
                    }
                ],
                "usage": {
                    "input_tokens": 1,
                    "output_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )

    client = AsyncOpenAI(
        api_key="teste",
        base_url="https://api.deepseek.com",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    answer = asyncio.run(
        ChatService(client, "deepseek-flash").reply(analise_minima(), [], "oi")
    )

    assert answer == "ok"
    assert captured["path"] == "/responses"
    body = captured["body"]
    assert body["model"] == "deepseek-flash"
    assert body["reasoning"] == {"effort": "none"}
    assert body["tool_choice"] == "auto"
    assert body["tools"][0]["name"] == "resumo"
    assert "function" not in body["tools"][0]
    assert body["input"] == [{"role": "user", "content": "oi"}]
    assert "CIÊNCIA DA COMPUTAÇÃO" in body["instructions"]
