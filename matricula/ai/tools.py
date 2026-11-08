"""Ferramentas que o modelo pode chamar sobre a análise."""

from __future__ import annotations

import json
from typing import Any, Callable

from ..core.format import DIAS, to_minutes
from ..core.models import Analise, Estado, OfertaDisciplina, Turma
from ..core.text import normalize_name

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "resumo",
        "description": "Retorna curso, período, se a oferta foi publicada e "
        "a contagem de disciplinas por estado.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
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
    {
        "type": "function",
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
    {
        "type": "function",
        "name": "listar_turmas",
        "description": "Lista apenas as turmas e horários de uma disciplina.",
        "parameters": {
            "type": "object",
            "properties": {"sigla": {"type": "string"}},
            "required": ["sigla"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "estado_da_grade",
        "description": "Retorna as disciplinas e turmas que o aluno já escolheu "
        "na grade, com créditos totais e conflitos de horário.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "adicionar_disciplina",
        "description": "Adiciona uma disciplina à grade do aluno. Se a turma "
        "não for informada, escolhe a primeira turma sem conflito.",
        "parameters": {
            "type": "object",
            "properties": {
                "sigla": {"type": "string"},
                "turma": {"type": "string"},
            },
            "required": ["sigla"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "trocar_turma",
        "description": "Troca a turma de uma disciplina que já está na grade.",
        "parameters": {
            "type": "object",
            "properties": {
                "sigla": {"type": "string"},
                "turma": {"type": "string"},
            },
            "required": ["sigla", "turma"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "remover_disciplina",
        "description": "Remove uma disciplina da grade do aluno.",
        "parameters": {
            "type": "object",
            "properties": {"sigla": {"type": "string"}},
            "required": ["sigla"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "montar_grade_sem_conflito",
        "description": "Monta uma grade sem conflitos de horário, priorizando "
        "disciplinas obrigatórias, etapas iniciais e mais créditos. Adiciona "
        "disciplinas ofertadas até o limite.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_disciplinas": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 12,
                },
                "incluir_eletivas": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
]


class AnalysisTools:
    """Implementação das ferramentas sobre uma análise concreta."""

    def __init__(
        self, analise: Analise, plano: list[dict[str, Any]] | None = None
    ) -> None:
        self._analise = analise
        self._plano = plano if plano is not None else []
        self._por_sigla = {
            oferta.disciplina.sigla: oferta for oferta in analise.ofertas
        }
        self._acoes: dict[str, Callable[..., Any]] = {
            "resumo": self.resumo,
            "listar_disciplinas": self.listar_disciplinas,
            "detalhar_disciplina": self.detalhar_disciplina,
            "listar_turmas": self.listar_turmas,
            "estado_da_grade": self.estado_da_grade,
            "adicionar_disciplina": self.adicionar_disciplina,
            "trocar_turma": self.trocar_turma,
            "remover_disciplina": self.remover_disciplina,
            "montar_grade_sem_conflito": self.montar_grade_sem_conflito,
        }

    @property
    def plano(self) -> list[dict[str, Any]]:
        return self._plano

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

    def estado_da_grade(self) -> dict[str, Any]:
        selecionadas: list[dict[str, Any]] = []
        invalidas: list[dict[str, Any]] = []
        sessoes: list[tuple[str, str, list[tuple[int, int, int]]]] = []
        vistos: set[str] = set()

        for escolha in self._plano:
            if not isinstance(escolha, dict):
                continue
            code = str(escolha.get("code") or "").strip().upper()
            letter = str(escolha.get("letter") or "").strip()
            if not code or code in vistos:
                continue

            oferta = self._por_sigla.get(code)
            if oferta is None:
                invalidas.append(
                    {"sigla": code, "turma": letter, "motivo": "fora da análise"}
                )
                continue

            turma = next((t for t in oferta.turmas if t.turma == letter), None)
            if turma is None:
                invalidas.append(
                    {"sigla": code, "turma": letter, "motivo": "turma não encontrada"}
                )
                continue

            vistos.add(code)
            encontros = []
            faixas = []
            for encontro in turma.encontros:
                if encontro.dia_semana is None:
                    continue
                inicio = to_minutes(encontro.hora_inicio)
                fim = to_minutes(encontro.hora_fim)
                if inicio is None or fim is None or fim <= inicio:
                    continue
                faixas.append((encontro.dia_semana, inicio, fim))
                encontros.append(
                    {
                        "dia": DIAS.get(encontro.dia_semana, str(encontro.dia_semana)),
                        "dia_semana": encontro.dia_semana,
                        "inicio": encontro.hora_inicio,
                        "fim": encontro.hora_fim,
                        "campus": encontro.campus,
                        "local": encontro.espaco,
                    }
                )

            selecionadas.append(
                {
                    "sigla": oferta.disciplina.sigla,
                    "nome": oferta.disciplina.nome,
                    "turma": turma.turma,
                    "carater": oferta.disciplina.carater,
                    "creditos": oferta.disciplina.creditos,
                    "estado": oferta.estado.value,
                    "encontros": encontros,
                }
            )
            sessoes.append((oferta.disciplina.sigla, turma.turma, faixas))

        conflitos = []
        for indice, (sigla_a, turma_a, faixas_a) in enumerate(sessoes):
            for sigla_b, turma_b, faixas_b in sessoes[indice + 1 :]:
                for dia_a, inicio_a, fim_a in faixas_a:
                    for dia_b, inicio_b, fim_b in faixas_b:
                        if dia_a != dia_b:
                            continue
                        if inicio_a < fim_b and inicio_b < fim_a:
                            conflitos.append(
                                {
                                    "a": {"sigla": sigla_a, "turma": turma_a},
                                    "b": {"sigla": sigla_b, "turma": turma_b},
                                    "dia": DIAS.get(dia_a, str(dia_a)),
                                    "inicio": _hhmm(max(inicio_a, inicio_b)),
                                    "fim": _hhmm(min(fim_a, fim_b)),
                                }
                            )

        return {
            "total_disciplinas": len(selecionadas),
            "total_creditos": sum(item["creditos"] for item in selecionadas),
            "selecionadas": selecionadas,
            "conflitos": conflitos,
            "invalidas": invalidas,
        }

    def adicionar_disciplina(
        self, sigla: str, turma: str | None = None
    ) -> dict[str, Any]:
        code = sigla.strip().upper()
        oferta = self._por_sigla.get(code)
        if oferta is None:
            return {
                "ok": False,
                "erro": f"disciplina {sigla} não está na lista de possibilidades",
            }

        if any(
            str(escolha.get("code") or "").strip().upper() == code
            for escolha in self._plano
        ):
            return {
                "ok": False,
                "erro": f"{code} já está na grade",
                "plano": _plano_copia(self._plano),
            }

        if oferta.estado is not Estado.OFERTADA:
            return {
                "ok": False,
                "erro": f"{code} não está ofertada neste período",
                "estado": oferta.estado.value,
            }

        if not oferta.turmas:
            return {"ok": False, "erro": f"{code} não tem turmas neste período"}

        if turma:
            escolhida = next(
                (t for t in oferta.turmas if t.turma == turma.strip()), None
            )
            if escolhida is None:
                return {
                    "ok": False,
                    "erro": f"turma {turma} não encontrada",
                    "turmas": [_turma_dict(t) for t in oferta.turmas],
                }
        else:
            escolhida = next(
                (
                    t
                    for t in oferta.turmas
                    if not self._conflitos_da_turma(t, code)
                ),
                None,
            )
            if escolhida is None:
                return {
                    "ok": False,
                    "erro": "todas as turmas conflitam com a grade atual; "
                    "escolha uma turma",
                    "turmas": [_turma_dict(t) for t in oferta.turmas],
                    "conflitos": self.estado_da_grade()["conflitos"],
                }

        self._plano.append(
            {"code": oferta.disciplina.sigla, "letter": escolhida.turma}
        )
        estado = self.estado_da_grade()
        return {
            "ok": True,
            "acao": "adicionada",
            "sigla": oferta.disciplina.sigla,
            "turma": escolhida.turma,
            "plano": _plano_copia(self._plano),
            "conflitos": estado["conflitos"],
            "total_creditos": estado["total_creditos"],
        }

    def trocar_turma(self, sigla: str, turma: str) -> dict[str, Any]:
        code = sigla.strip().upper()
        escolha = next(
            (
                e
                for e in self._plano
                if str(e.get("code") or "").strip().upper() == code
            ),
            None,
        )
        if escolha is None:
            return {
                "ok": False,
                "erro": f"{code} não está na grade; use adicionar_disciplina",
            }

        oferta = self._por_sigla.get(code)
        if oferta is None:
            return {
                "ok": False,
                "erro": f"{code} não está na lista de possibilidades",
            }

        nova = next((t for t in oferta.turmas if t.turma == turma.strip()), None)
        if nova is None:
            return {
                "ok": False,
                "erro": f"turma {turma} não encontrada",
                "turmas": [_turma_dict(t) for t in oferta.turmas],
            }

        escolha["letter"] = nova.turma
        estado = self.estado_da_grade()
        return {
            "ok": True,
            "acao": "turma_alterada",
            "sigla": code,
            "turma": nova.turma,
            "plano": _plano_copia(self._plano),
            "conflitos": estado["conflitos"],
            "total_creditos": estado["total_creditos"],
        }

    def remover_disciplina(self, sigla: str) -> dict[str, Any]:
        code = sigla.strip().upper()
        antes = len(self._plano)
        self._plano[:] = [
            escolha
            for escolha in self._plano
            if str(escolha.get("code") or "").strip().upper() != code
        ]
        removida = len(self._plano) != antes
        estado = self.estado_da_grade()
        return {
            "ok": removida,
            "acao": "removida" if removida else "nao_encontrada",
            "sigla": code,
            "plano": _plano_copia(self._plano),
            "conflitos": estado["conflitos"],
            "total_creditos": estado["total_creditos"],
        }

    def montar_grade_sem_conflito(
        self, max_disciplinas: int = 6, incluir_eletivas: bool = True
    ) -> dict[str, Any]:
        try:
            limite = int(max_disciplinas)
        except (TypeError, ValueError):
            limite = 6
        limite = max(1, min(limite, 12))

        if len(self._plano) >= limite:
            estado = self.estado_da_grade()
            return {
                "ok": True,
                "adicionadas": [],
                "aviso": "limite já atingido",
                "plano": _plano_copia(self._plano),
                "conflitos": estado["conflitos"],
                "total_creditos": estado["total_creditos"],
                "total_disciplinas": estado["total_disciplinas"],
            }

        atuais = {
            str(escolha.get("code") or "").strip().upper()
            for escolha in self._plano
        }
        candidatas = []
        for oferta in self._analise.ofertas:
            disciplina = oferta.disciplina
            if disciplina.sigla in atuais:
                continue
            if oferta.estado is not Estado.OFERTADA or not oferta.turmas:
                continue
            if (
                not incluir_eletivas
                and normalize_name(disciplina.carater) != "OBRIGATORIA"
            ):
                continue
            candidatas.append(oferta)

        candidatas.sort(
            key=lambda oferta: (
                0
                if normalize_name(oferta.disciplina.carater) == "OBRIGATORIA"
                else 1,
                oferta.disciplina.etapa
                if oferta.disciplina.etapa is not None
                else 99,
                -oferta.disciplina.creditos,
                oferta.disciplina.sigla,
            )
        )

        adicionadas = []
        for oferta in candidatas:
            if len(self._plano) >= limite:
                break
            disciplina = oferta.disciplina
            escolhida = next(
                (
                    turma
                    for turma in oferta.turmas
                    if not self._conflitos_da_turma(turma, disciplina.sigla)
                ),
                None,
            )
            if escolhida is None:
                continue
            self._plano.append(
                {"code": disciplina.sigla, "letter": escolhida.turma}
            )
            adicionadas.append(
                {
                    "sigla": disciplina.sigla,
                    "nome": disciplina.nome,
                    "turma": escolhida.turma,
                }
            )

        estado = self.estado_da_grade()
        return {
            "ok": True,
            "adicionadas": adicionadas,
            "plano": _plano_copia(self._plano),
            "conflitos": estado["conflitos"],
            "total_creditos": estado["total_creditos"],
            "total_disciplinas": estado["total_disciplinas"],
        }

    def _conflitos_da_turma(
        self, turma: Turma, ignorar: str
    ) -> list[dict[str, Any]]:
        candidato = _faixas(turma)
        if not candidato:
            return []

        conflitos = []
        for escolha in self._plano:
            code = str(escolha.get("code") or "").strip().upper()
            if code == ignorar:
                continue
            oferta = self._por_sigla.get(code)
            if oferta is None:
                continue
            atual = next(
                (t for t in oferta.turmas if t.turma == escolha.get("letter")),
                None,
            )
            if atual is None:
                continue
            for dia_a, inicio_a, fim_a in candidato:
                for dia_b, inicio_b, fim_b in _faixas(atual):
                    if dia_a != dia_b:
                        continue
                    if inicio_a < fim_b and inicio_b < fim_a:
                        conflitos.append(
                            {
                                "a": {"sigla": code, "turma": atual.turma},
                                "b": {
                                    "sigla": oferta.disciplina.sigla,
                                    "turma": turma.turma,
                                },
                                "dia": DIAS.get(dia_a, str(dia_a)),
                                "inicio": _hhmm(max(inicio_a, inicio_b)),
                                "fim": _hhmm(min(fim_a, fim_b)),
                            }
                        )
        return conflitos


def _faixas(turma: Turma) -> list[tuple[int, int, int]]:
    faixas = []
    for encontro in turma.encontros:
        if encontro.dia_semana is None:
            continue
        inicio = to_minutes(encontro.hora_inicio)
        fim = to_minutes(encontro.hora_fim)
        if inicio is None or fim is None or fim <= inicio:
            continue
        faixas.append((encontro.dia_semana, inicio, fim))
    return faixas


def _plano_copia(plano: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(escolha) for escolha in plano]


def _hhmm(minutos: int) -> str:
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


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
