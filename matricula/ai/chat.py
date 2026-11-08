"""Orquestração do chat com tool calling sobre uma análise."""

from __future__ import annotations

import logging
from typing import Any, Iterable

from ..core.models import Analise
from .prompt import build_system_prompt
from .tools import TOOL_SCHEMAS, AnalysisTools

logger = logging.getLogger(__name__)

MAX_STEPS = 4
FALLBACK = "Não consegui formular uma resposta agora. Tente reformular a pergunta."


class ChatService:
    """Cliente OpenAI-compatível (DeepSeek) com ferramentas da análise."""

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model

    def reply(self, analise: Analise, history: Iterable[Any], pergunta: str) -> str:
        tools = AnalysisTools(analise)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(analise)}
        ]
        messages.extend(
            {"role": mensagem.role, "content": mensagem.content}
            for mensagem in history
            if mensagem.role in {"user", "assistant"}
        )
        messages.append({"role": "user", "content": pergunta})

        for _ in range(MAX_STEPS):
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            message = response.choices[0].message
            tool_calls = _get(message, "tool_calls") or []
            if not tool_calls:
                content = _get(message, "content")
                return (content or "").strip() or FALLBACK

            messages.append(_assistant_message(message, tool_calls))
            for call in tool_calls:
                call_id, name, arguments = _call_parts(call)
                result = tools.call(name, arguments)
                logger.info("tool %s -> %.200s", name, result)
                messages.append(
                    {"role": "tool", "tool_call_id": call_id, "content": result}
                )

        return (
            "Não consegui concluir a análise em tempo hábil. "
            "Tente uma pergunta mais específica."
        )


def _get(message: Any, key: str) -> Any:
    if isinstance(message, dict):
        return message.get(key)
    return getattr(message, key, None)


def _assistant_message(message: Any, tool_calls: list[Any]) -> dict[str, Any]:
    content = _get(message, "content")
    payload: dict[str, Any] = {"role": "assistant"}
    if content:
        payload["content"] = content
    payload["tool_calls"] = [_call_dict(call) for call in tool_calls]
    return payload


def _call_dict(call: Any) -> dict[str, Any]:
    if isinstance(call, dict):
        return call
    if hasattr(call, "model_dump"):
        return call.model_dump(exclude_none=True)
    function = getattr(call, "function", None)
    return {
        "id": getattr(call, "id", None),
        "type": "function",
        "function": {
            "name": getattr(function, "name", None),
            "arguments": getattr(function, "arguments", None),
        },
    }


def _call_parts(call: Any) -> tuple[str, str, str]:
    if isinstance(call, dict):
        function = call.get("function") or {}
        return call.get("id", ""), function.get("name", ""), function.get("arguments") or "{}"
    function = getattr(call, "function", None)
    return (
        getattr(call, "id", ""),
        getattr(function, "name", ""),
        getattr(function, "arguments", None) or "{}",
    )
