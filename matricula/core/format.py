"""Formatação de horários compartilhada entre CLI e interface web."""

from __future__ import annotations

from .models import Turma

DIAS = {2: "seg", 3: "ter", 4: "qua", 5: "qui", 6: "sex", 7: "sáb"}


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
