"""Renderização segura de Markdown das respostas do modelo."""

from __future__ import annotations

import html

import markdown
from markupsafe import Markup


def render_markdown(text: str) -> Markup:
    """Escapa HTML antes de renderizar, para não injetar markup do modelo."""
    return Markup(
        markdown.markdown(html.escape(text), extensions=["extra", "sane_lists"])
    )
