"""Configuração do provedor OpenAI-compatível (DeepSeek por padrão)."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.deepseek.com"
# "deepseek-chat" foi descontinuado em 2026-07-24; os modelos atuais são
# "deepseek-flash" (V4.1 Flash) e "deepseek-v4-pro".
DEFAULT_MODEL = "deepseek-flash"


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_key=(os.getenv("DEEPSEEK_API_KEY") or "").strip() or None,
            base_url=(os.getenv("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL).strip(),
            model=(os.getenv("DEEPSEEK_MODEL") or DEFAULT_MODEL).strip(),
        )

    @property
    def configured(self) -> bool:
        return self.api_key is not None
