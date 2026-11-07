"""Parsing do HTML exportado da tela "Possibilidade de Matrícula"."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .errors import ParseError
from .models import DisciplinaPossivel, Possibilidades

# "ORGANIZAÇÃO DE COMPUTADORES - (INF01113)"
_DISCIPLINA = re.compile(r"^(?P<nome>.*?)\s*-\s*\((?P<sigla>[A-Z0-9]+)\)\s*$")
_ATIVIDADE = re.compile(r"AtividadeEnsino=(\d+)_\d+")
_ABRE_HORARIO = re.compile(r"AbreHorario\(([^)]*)\)")
_VINCULO = re.compile(r"V[íi]nculo\s+em\s+(\d{4})/(\d)")
_ROW_CLASSES = {"modelo1odd", "modelo1even"}


def decode_html(raw: bytes) -> str:
    """O Portal exporta em ISO-8859-1; cp1252 cobre os acentos usados."""
    for encoding in ("cp1252", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp1252", errors="replace")


def parse_possibilidades(raw: bytes) -> Possibilidades:
    """Extrai curso, período e disciplinas do HTML do Portal do Aluno."""
    text = decode_html(raw)
    soup = BeautifulSoup(text, "html.parser")

    table = soup.find("table", id="poss")
    if table is None:
        raise ParseError('tabela "poss" não encontrada no HTML')

    lines = [line.strip() for line in soup.get_text("\n").splitlines()]
    curso = _value_after_label(lines, "Curso:")
    if not curso:
        raise ParseError('campo "Curso" não encontrado no HTML')

    periodo = _periodo(lines, text)
    if not periodo:
        raise ParseError("período letivo não encontrado no HTML")

    disciplinas = [
        disciplina
        for row in table.find_all("tr")
        if _ROW_CLASSES & set(row.get("class") or [])
        if (disciplina := _parse_row(row)) is not None
    ]
    if not disciplinas:
        raise ParseError("nenhuma disciplina encontrada na tabela")

    return Possibilidades(
        curso=curso,
        habilitacao=_value_after_label(lines, "Habilitação:"),
        curriculo=_value_after_label(lines, "Currículo:"),
        periodo=periodo,
        disciplinas=disciplinas,
    )


def _parse_row(row) -> DisciplinaPossivel | None:
    cells = row.find_all("td", recursive=False)
    if len(cells) < 6:
        return None

    anchor = cells[1].find("a")
    label = (anchor or cells[1]).get_text(" ", strip=True)
    match = _DISCIPLINA.match(label)
    if match is None:
        return None

    href = anchor.get("href", "") if anchor else ""
    atividade = _ATIVIDADE.search(href)
    if atividade is None:
        for link in row.find_all("a"):
            atividade = _ATIVIDADE.search(link.get("href", ""))
            if atividade is not None:
                break
    sigla = match.group("sigla")

    return DisciplinaPossivel(
        sigla=sigla,
        nome=match.group("nome").strip(),
        atividade_id=atividade.group(1) if atividade else None,
        etapa=_to_int(cells[2].get_text()),
        carater=cells[3].get_text(strip=True),
        creditos=_to_int(cells[4].get_text()) or 0,
        ch_total=_to_int(cells[5].get_text()) or 0,
        ch_extensao=_to_int(cells[6].get_text()) if len(cells) > 6 else None,
        administrativa=sigla.startswith("VAERE"),
    )


def _value_after_label(lines: list[str], label: str) -> str | None:
    for index, line in enumerate(lines):
        if not line.startswith(label):
            continue
        remainder = line[len(label) :].strip()
        if remainder:
            return remainder
        for following in lines[index + 1 :]:
            if following:
                return following
    return None


def _periodo(lines: list[str], text: str) -> str | None:
    for line in lines:
        match = _VINCULO.search(line)
        if match:
            return f"{match.group(1)}/{match.group(2)}"

    # Fallback: o código em AbreHorario(..., 2026022) é AAAA0S?.
    match = _ABRE_HORARIO.search(text)
    if match:
        code = match.group(1).split(",")[-1].strip()
        if re.fullmatch(r"\d{7}", code) and code[5] in "123":
            return f"{code[:4]}/{code[5]}"
    return None


def _to_int(value: str) -> int | None:
    digits = re.sub(r"\D", "", value)
    return int(digits) if digits else None
