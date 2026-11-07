"""Filtros aplicados na lista de ofertas."""

from __future__ import annotations

from ..core.models import OfertaDisciplina
from ..core.text import normalize_name

CARATERES = {"obrigatoria": "OBRIGATORIA", "eletiva": "ELETIVA"}


def filter_ofertas(
    ofertas: list[OfertaDisciplina],
    estado: str = "",
    carater: str = "",
    q: str = "",
) -> list[OfertaDisciplina]:
    carater_alvo = CARATERES.get(carater)
    busca = normalize_name(q)
    resultado = []
    for oferta in ofertas:
        disciplina = oferta.disciplina
        if estado and oferta.estado.value != estado:
            continue
        if carater_alvo and normalize_name(disciplina.carater) != carater_alvo:
            continue
        if busca and busca not in normalize_name(disciplina.nome) and busca not in disciplina.sigla:
            continue
        resultado.append(oferta)
    return resultado
