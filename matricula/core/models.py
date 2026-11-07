"""Modelos de domínio do assistente de matrícula."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Encontro(BaseModel):
    """Um encontro semanal de uma turma."""

    dia_semana: int | None = None
    hora_inicio: str | None = None
    hora_fim: str | None = None
    campus: str | None = None
    espaco: str | None = None
    descricao_local: str | None = None


class Turma(BaseModel):
    """Uma turma ofertada, com todos os seus encontros."""

    sigla: str
    nome: str
    turma: str
    encontros: list[Encontro] = Field(default_factory=list)


class DisciplinaPossivel(BaseModel):
    """Uma disciplina que o aluno pode querer cursar, segundo o Portal."""

    sigla: str
    nome: str
    atividade_id: str | None = None
    etapa: int | None = None
    carater: str
    creditos: int
    ch_total: int
    ch_extensao: int | None = None
    administrativa: bool = False


class Possibilidades(BaseModel):
    """Retrato da tela "Possibilidade de Matrícula" de um aluno."""

    curso: str
    habilitacao: str | None = None
    curriculo: str | None = None
    periodo: str
    disciplinas: list[DisciplinaPossivel]


class Estado(StrEnum):
    """Disponibilidade de uma disciplina no período analisado."""

    OFERTADA = "ofertada"
    NAO_OFERTADA = "nao_ofertada"
    NAO_PUBLICADO = "nao_publicado"


class OfertaDisciplina(BaseModel):
    """Resultado da junção entre possibilidade e oferta do período."""

    disciplina: DisciplinaPossivel
    estado: Estado
    turmas: list[Turma] = Field(default_factory=list)


class Resumo(BaseModel):
    total: int
    ofertadas: int
    nao_ofertadas: int
    nao_publicadas: int


class Analise(BaseModel):
    """Resposta completa do núcleo para uma possibilidade de matrícula."""

    possibilidades: Possibilidades
    curso_id: str
    periodo_publicado: bool
    ofertas: list[OfertaDisciplina]
    resumo: Resumo
