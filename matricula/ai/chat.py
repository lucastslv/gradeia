"""Orquestração do chat com a Responses API (stateless) e tool calling."""

from __future__ import annotations

import logging
from typing import Any, Iterable

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

    def reply(self, analise: Analise, history: Iterable[Any], pergunta: str) -> str:
        tools = AnalysisTools(analise)
        input_items: list[dict[str, Any]] = [
            {"role": mensagem.role, "content": mensagem.content}
            for mensagem in history
            if mensagem.role in {"user", "assistant"}
        ]
        input_items.append({"role": "user", "content": pergunta})

        for _ in range(MAX_STEPS):
            response = self._client.responses.create(
                model=self._model,
                instructions=build_system_prompt(analise),
                input=input_items,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                reasoning=REASONING_DISABLED,
            )

            output = list(getattr(response, "output", None) or [])
            calls = [item for item in output if _item_type(item) == "function_call"]
            if not calls:
                return _output_text(response) or FALLBACK

            # Reenvia a saída do modelo (message/reasoning/function_call) e
            # acrescenta o resultado de cada ferramenta.
            input_items.extend(_item_dict(item) for item in output)
            for call in calls:
                call_id, name, arguments = _call_parts(call)
                result = tools.call(name, arguments)
                logger.info("tool %s -> %.200s", name, result)
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": result,
                    }
                )

        return (
            "Não consegui concluir a análise em tempo hábil. "
            "Tente uma pergunta mais específica."
        )


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
