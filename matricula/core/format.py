"""Formatação de horários compartilhada entre CLI e interface web."""

from __future__ import annotations

from .models import Turma

DIAS = {2: "seg", 3: "ter", 4: "qua", 5: "qui", 6: "sex", 7: "sáb"}


def to_minutes(value: str | None) -> int | None:
    """Converte "08:30" em 510. Devolve None para valor inválido."""
    if not value:
        return None
    try:
        hour, minute = value.split(":")[:2]
        return int(hour) * 60 + int(minute)
    except (ValueError, AttributeError):
        return None


def format_encontros(turma: Turma) -> str:
    return ", ".join(
        f"{DIAS.get(encontro.dia_semana, str(encontro.dia_semana))} "
        f"{encontro.hora_inicio}-{encontro.hora_fim}"
        for encontro in turma.encontros
    )


def format_turma(turma: Turma) -> str:
    campus = next((e.campus for e in turma.encontros if e.campus), None)
    local = f" · {campus}" if campus else ""
    return f"turma {turma.turma}: {format_encontros(turma)}{local}"
