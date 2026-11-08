"""Ferramentas que o modelo pode chamar sobre a análise."""

from __future__ import annotations

import json
from typing import Any, Callable

from ..core.format import DIAS
from ..core.models import Analise, Estado, OfertaDisciplina, Turma
from ..core.text import normalize_name

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "resumo",
            "description": "Retorna curso, período, se a oferta foi publicada e "
            "a contagem de disciplinas por estado.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_disciplinas",
            "description": "Lista disciplinas da possibilidade de matrícula, com "
            "filtros opcionais por estado, caráter e texto (nome ou sigla).",
            "parameters": {
                "type": "object",
                "properties": {
                    "estado": {
                        "type": "string",
                        "enum": ["ofertada", "nao_ofertada", "nao_publicado"],
                    },
                    "carater": {
                        "type": "string",
                        "enum": ["Obrigatória", "Eletiva"],
                    },
                    "busca": {"type": "string"},
                    "limite": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detalhar_disciplina",
            "description": "Retorna todos os dados de uma disciplina e suas turmas "
            "com horários e campus.",
            "parameters": {
                "type": "object",
                "properties": {"sigla": {"type": "string"}},
                "required": ["sigla"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_turmas",
            "description": "Lista apenas as turmas e horários de uma disciplina.",
            "parameters": {
                "type": "object",
                "properties": {"sigla": {"type": "string"}},
                "required": ["sigla"],
                "additionalProperties": False,
            },
        },
    },
]


class AnalysisTools:
    """Implementação das ferramentas sobre uma análise concreta."""

    def __init__(self, analise: Analise) -> None:
        self._analise = analise
        self._por_sigla = {
            oferta.disciplina.sigla: oferta for oferta in analise.ofertas
        }
        self._acoes: dict[str, Callable[..., Any]] = {
            "resumo": self.resumo,
            "listar_disciplinas": self.listar_disciplinas,
            "detalhar_disciplina": self.detalhar_disciplina,
            "listar_turmas": self.listar_turmas,
        }

    def call(self, name: str, arguments: str | None) -> str:
        acao = self._acoes.get(name)
        if acao is None:
            return _json({"erro": f"ferramenta desconhecida: {name}"})

        try:
            args = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return _json({"erro": "argumentos inválidos"})

        if not isinstance(args, dict):
            return _json({"erro": "argumentos devem ser um objeto"})

        try:
            return _json(acao(**args))
        except TypeError as exc:
            return _json({"erro": f"argumentos inválidos: {exc}"})

    def resumo(self) -> dict[str, Any]:
        possibilidades = self._analise.possibilidades
        resumo = self._analise.resumo
        return {
            "curso": possibilidades.curso,
            "periodo": possibilidades.periodo,
            "periodo_publicado": self._analise.periodo_publicado,
            "total": resumo.total,
            "ofertadas": resumo.ofertadas,
            "nao_ofertadas": resumo.nao_ofertadas,
            "nao_publicadas": resumo.nao_publicadas,
        }

    def listar_disciplinas(
        self,
        estado: str | None = None,
        carater: str | None = None,
        busca: str | None = None,
        limite: int = 50,
    ) -> dict[str, Any]:
        if estado and estado not in {e.value for e in Estado}:
            return {"erro": f"estado inválido: {estado}"}

        alvo = normalize_name(busca) if busca else ""
        carater_alvo = normalize_name(carater) if carater else ""

        itens = []
        for oferta in self._analise.ofertas:
            disciplina = oferta.disciplina
            if estado and oferta.estado.value != estado:
                continue
            if carater_alvo and normalize_name(disciplina.carater) != carater_alvo:
                continue
            if alvo and alvo not in normalize_name(disciplina.nome) and alvo not in disciplina.sigla:
                continue
            itens.append(_disciplina_dict(oferta))

        limite = max(1, min(int(limite), 50))
        return {"total": len(itens), "itens": itens[:limite]}

    def detalhar_disciplina(self, sigla: str) -> dict[str, Any]:
        oferta = self._por_sigla.get(sigla.strip().upper())
        if oferta is None:
            return {"erro": f"disciplina {sigla} não está na lista de possibilidades"}
        return {
            **_disciplina_dict(oferta),
            "turmas": [_turma_dict(turma) for turma in oferta.turmas],
        }

    def listar_turmas(self, sigla: str) -> dict[str, Any]:
        oferta = self._por_sigla.get(sigla.strip().upper())
        if oferta is None:
            return {"erro": f"disciplina {sigla} não está na lista de possibilidades"}
        return {
            "sigla": oferta.disciplina.sigla,
            "estado": oferta.estado.value,
            "turmas": [_turma_dict(turma) for turma in oferta.turmas],
        }


def _disciplina_dict(oferta: OfertaDisciplina) -> dict[str, Any]:
    disciplina = oferta.disciplina
    return {
        "sigla": disciplina.sigla,
        "nome": disciplina.nome,
        "etapa": disciplina.etapa,
        "carater": disciplina.carater,
        "creditos": disciplina.creditos,
        "ch_total": disciplina.ch_total,
        "estado": oferta.estado.value,
        "qtd_turmas": len(oferta.turmas),
    }


def _turma_dict(turma: Turma) -> dict[str, Any]:
    return {
        "turma": turma.turma,
        "campus": next((e.campus for e in turma.encontros if e.campus), None),
        "encontros": [
            {
                "dia": DIAS.get(encontro.dia_semana, str(encontro.dia_semana)),
                "dia_semana": encontro.dia_semana,
                "inicio": encontro.hora_inicio,
                "fim": encontro.hora_fim,
                "local": encontro.espaco,
            }
            for encontro in turma.encontros
        ],
    }


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
