"""Orquestração do chat com a Responses API (stateless), com streaming."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Iterable
from typing import Any

from ..core.models import Analise
from .prompt import build_system_prompt
from .tools import TOOL_SCHEMAS, AnalysisTools

logger = logging.getLogger(__name__)

MAX_STEPS = 4
FALLBACK = "Não consegui formular uma resposta agora. Tente reformular a pergunta."
# A Responses API é stateless e o thinking vem ligado por padrão. Desligamos
# para não pagar latência/tokens de raciocínio num chat de consulta.
REASONING_DISABLED = {"effort": "none"}


class ChatService:
    """Cliente OpenAI-compatível usando `/responses` (DeepSeek)."""

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model

    async def reply(
        self,
        analise: Analise,
        history: Iterable[Any],
        pergunta: str,
        plano: list[dict[str, Any]] | None = None,
    ) -> str:
        tools = AnalysisTools(analise, plano=plano)
        input_items = _input_items(history, pergunta)

        for _ in range(MAX_STEPS):
            response = await self._client.responses.create(
                **_request(self._model, analise, input_items)
            )
            output = list(getattr(response, "output", None) or [])
            calls = _function_calls(output)
            if not calls:
                return _output_text(response) or FALLBACK

            input_items.extend(_item_dict(item) for item in output)
            input_items.extend(_tool_outputs(calls, tools))

        return (
            "Não consegui concluir a análise em tempo hábil. "
            "Tente uma pergunta mais específica."
        )

    async def stream_reply(
        self,
        analise: Analise,
        history: Iterable[Any],
        pergunta: str,
        plano: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Emite eventos `delta`, `reset`, `done` e `error`."""
        tools = AnalysisTools(analise, plano=plano)
        input_items = _input_items(history, pergunta)

        for _ in range(MAX_STEPS):
            stream = await self._client.responses.create(
                **_request(self._model, analise, input_items),
                stream=True,
            )

            text = ""
            response = None
            failed = False
            async for event in stream:
                event_type = _event_type(event)
                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", "") or ""
                    if delta:
                        text += delta
                        yield {"type": "delta", "text": delta}
                elif event_type in {
                    "response.completed",
                    "response.incomplete",
                }:
                    response = getattr(event, "response", None)
                elif event_type == "response.failed":
                    response = getattr(event, "response", None)
                    failed = True

            if failed:
                yield {"type": "error", "text": "Não consegui concluir a resposta."}
                return
            if response is None:
                yield {"type": "done", "text": text or FALLBACK}
                return

            output = list(getattr(response, "output", None) or [])
            calls = _function_calls(output)
            if not calls:
                final = (text or _output_text(response)).strip() or FALLBACK
                yield {"type": "done", "text": final}
                return

            # O texto emitido antes de uma tool call é descartado no cliente;
            # a resposta final vem na próxima rodada do stream.
            if text:
                yield {"type": "reset"}
            input_items.extend(_item_dict(item) for item in output)
            antes = _plano_chave(tools.plano)
            input_items.extend(_tool_outputs(calls, tools))
            if _plano_chave(tools.plano) != antes:
                yield {"type": "plano", "plano": _plano_copia(tools.plano)}

        yield {
            "type": "done",
            "text": "Não consegui concluir a análise em tempo hábil. "
            "Tente uma pergunta mais específica.",
        }


def _request(model: str, analise: Analise, input_items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model": model,
        "instructions": build_system_prompt(analise),
        "input": input_items,
        "tools": TOOL_SCHEMAS,
        "tool_choice": "auto",
        "reasoning": REASONING_DISABLED,
    }


def _input_items(history: Iterable[Any], pergunta: str) -> list[dict[str, Any]]:
    items = [
        {"role": mensagem.role, "content": mensagem.content}
        for mensagem in history
        if mensagem.role in {"user", "assistant"}
    ]
    items.append({"role": "user", "content": pergunta})
    return items


def _function_calls(output: list[Any]) -> list[Any]:
    return [item for item in output if _item_type(item) == "function_call"]


def _tool_outputs(calls: list[Any], tools: AnalysisTools) -> list[dict[str, Any]]:
    results = []
    for call in calls:
        call_id, name, arguments = _call_parts(call)
        result = tools.call(name, arguments)
        logger.info("tool %s -> %.200s", name, result)
        results.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": result,
            }
        )
    return results


def _event_type(event: Any) -> str | None:
    if isinstance(event, dict):
        return event.get("type")
    return getattr(event, "type", None)


def _item_type(item: Any) -> str | None:
    if isinstance(item, dict):
        return item.get("type")
    return getattr(item, "type", None)


def _item_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    if hasattr(item, "model_dump"):
        return item.model_dump(exclude_none=True)

    data: dict[str, Any] = {"type": _item_type(item)}
    for key in ("id", "status", "role", "call_id", "name", "arguments"):
        value = getattr(item, key, None)
        if value is not None:
            data[key] = value
    content = getattr(item, "content", None)
    if content is not None:
        data["content"] = [_part_dict(part) for part in content]
    return data


def _part_dict(part: Any) -> dict[str, Any]:
    if isinstance(part, dict):
        return part
    if hasattr(part, "model_dump"):
        return part.model_dump(exclude_none=True)
    return {"type": getattr(part, "type", None), "text": getattr(part, "text", None)}


def _output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return str(text).strip()

    parts: list[str] = []
    for item in getattr(response, "output", None) or []:
        if _item_type(item) != "message":
            continue
        content = item.get("content") if isinstance(item, dict) else getattr(item, "content", None)
        for part in content or []:
            part_type = (
                part.get("type") if isinstance(part, dict) else getattr(part, "type", None)
            )
            part_text = (
                part.get("text") if isinstance(part, dict) else getattr(part, "text", None)
            )
            if part_type == "output_text" and part_text:
                parts.append(part_text)
    return "".join(parts).strip()


def _call_parts(call: Any) -> tuple[str, str, str]:
    if isinstance(call, dict):
        return (
            call.get("call_id", ""),
            call.get("name", ""),
            call.get("arguments") or "{}",
        )
    return (
        getattr(call, "call_id", ""),
        getattr(call, "name", ""),
        getattr(call, "arguments", None) or "{}",
    )


def _plano_chave(plano: list[dict[str, Any]]) -> str:
    return json.dumps(plano, sort_keys=True, ensure_ascii=False)


def _plano_copia(plano: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(escolha) for escolha in plano]
