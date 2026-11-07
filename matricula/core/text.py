"""Normalização de texto usada para casar nomes entre o Portal e a API."""

from __future__ import annotations

import re
import unicodedata


def normalize_name(value: str) -> str:
    """Maiúsculas, sem acentos e com espaços colapsados."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents).strip().upper()
