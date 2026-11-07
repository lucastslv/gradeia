"""CLI para rodar o núcleo sem interface web."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core.api import UfrgsApi
from .core.cache import SqliteCache
from .core.models import Analise, Estado, Turma
from .service.possibilidades import analisar_html

DIAS = {2: "seg", 3: "ter", 4: "qua", 5: "qui", 6: "sex", 7: "sáb"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="matricula",
        description="Verifica quais disciplinas da Possibilidade de Matrícula "
        "estão ofertadas no período do próprio arquivo.",
    )
    parser.add_argument("html", type=Path, help="HTML exportado do Portal do Aluno")
    parser.add_argument(
        "--json", action="store_true", help="Emite a análise completa em JSON"
    )
    args = parser.parse_args(argv)

    api = UfrgsApi(cache=SqliteCache())
    try:
        analise = analisar_html(args.html.read_bytes(), api)
    finally:
        api.close()

    if args.json:
        print(analise.model_dump_json(indent=2))
    else:
        print_report(analise)
    return 0


def print_report(analise: Analise) -> None:
    possibilidades = analise.possibilidades
    resumo = analise.resumo

    print(f"{possibilidades.curso} · {possibilidades.periodo}")
    print(
        f"{resumo.total} disciplinas · {resumo.ofertadas} ofertadas · "
        f"{resumo.nao_ofertadas} não ofertadas · "
        f"{resumo.nao_publicadas} pendentes de publicação"
    )
    if not analise.periodo_publicado:
        print(
            f"\nA oferta de {possibilidades.periodo} ainda não foi publicada; "
            "as disciplinas não foram avaliadas."
        )
        return

    print()
    header = (
        f"{'SIGLA':<9} {'DISCIPLINA':<40} {'ET':>2} {'CARÁTER':<12} "
        f"{'CR':>2}  ESTADO"
    )
    print(header)
    print("-" * len(header))
    for oferta in analise.ofertas:
        disciplina = oferta.disciplina
        etapa = "-" if disciplina.etapa is None else str(disciplina.etapa)
        print(
            f"{disciplina.sigla:<9} {_truncate(disciplina.nome, 40):<40} "
            f"{etapa:>2} {disciplina.carater:<12} {disciplina.creditos:>2}  "
            f"{_estado(oferta.estado)}"
        )
        for turma in oferta.turmas:
            print(f"          {_turma(turma)}")


def _estado(estado: Estado) -> str:
    return {
        Estado.OFERTADA: "ofertada",
        Estado.NAO_OFERTADA: "não ofertada",
        Estado.NAO_PUBLICADO: "não publicado",
    }[estado]


def _turma(turma: Turma) -> str:
    encontros = ", ".join(
        f"{DIAS.get(encontro.dia_semana, str(encontro.dia_semana))} "
        f"{encontro.hora_inicio}-{encontro.hora_fim}"
        for encontro in turma.encontros
    )
    campus = next((e.campus for e in turma.encontros if e.campus), None)
    local = f" · {campus}" if campus else ""
    return f"turma {turma.turma}: {encontros}{local}"


def _truncate(value: str, size: int) -> str:
    return value if len(value) <= size else value[: size - 1] + "…"


if __name__ == "__main__":
    sys.exit(main())
