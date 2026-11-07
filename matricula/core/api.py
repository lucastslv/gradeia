"""Cliente das APIs públicas de graduação da UFRGS."""

from __future__ import annotations

from typing import Any

import httpx

from .cache import Cache, NullCache
from .errors import AmbiguousCourse, ApiError, CourseNotFound
from .models import Encontro, Turma
from .text import normalize_name

BASE_URL = "https://api.ufrgs.br"
CURSOS_PATH = "/v2/dados-abertos/graduacao/cursos"
TURMAS_PATH = "/v2/graduacao/turmas"
PER_PAGE = 1000


class UfrgsApi:
    """Acesso aos endpoints de cursos e turmas, com paginação e cache."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        cache: Cache | None = None,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._cache = cache or NullCache()

    def close(self) -> None:
        if self._client is not None and self._owns_client:
            self._client.close()
            self._client = None

    def resolve_curso(self, nome: str, grau: str | None = None) -> str:
        """Resolve o nome do curso (como aparece no Portal) para o id da API."""
        cursos = self.list_cursos()
        target = normalize_name(nome)
        matches = [c for c in cursos if normalize_name(c["Curso"]) == target]
        if not matches:
            raise CourseNotFound(f"curso {nome!r} não encontrado na API")

        if grau:
            wanted = normalize_name(grau)
            by_grau = [
                c
                for c in matches
                if normalize_name(c["Grau"]) in wanted
                or wanted.startswith(normalize_name(c["Grau"]))
            ]
            matches = by_grau or matches

        ids = sorted({c["Identificador"] for c in matches})
        if len(ids) > 1:
            raise AmbiguousCourse(nome, ids)
        return ids[0]

    def list_cursos(self) -> list[dict[str, Any]]:
        cached = self._cache.get("cursos")
        if cached is not None:
            return cached

        unique: dict[tuple[str, str, str], dict[str, Any]] = {}
        for item in self._paginate(CURSOS_PATH, "items"):
            key = (
                item.get("Identificador", ""),
                item.get("Curso", ""),
                item.get("Grau", ""),
            )
            unique.setdefault(key, item)

        cursos = list(unique.values())
        self._cache.set("cursos", cursos, ttl_seconds=24 * 60 * 60)
        return cursos

    def period_total(self, periodo: str) -> int:
        """Quantas turmas existem no período. Zero significa "não publicado"."""
        key = f"period_total:{periodo}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        data = self._get(TURMAS_PATH, {"periodo": periodo, "per-page": 1})
        total = int((data.get("_meta") or {}).get("totalCount") or 0)
        self._cache.set(key, total, ttl_seconds=5 * 60)
        return total

    def list_turmas(self, periodo: str, curso_id: str) -> list[Turma]:
        key = f"turmas:{periodo}:{curso_id}"
        cached = self._cache.get(key)
        if cached is not None:
            return [Turma.model_validate(item) for item in cached]

        grouped: dict[tuple[str, str], Turma] = {}
        for item in self._paginate(
            TURMAS_PATH, "turmas", {"periodo": periodo, "curso": curso_id}
        ):
            sigla = (item.get("Sigla") or "").strip()
            if not sigla:
                continue
            turma = (item.get("Turma") or "").strip()
            key_turma = (sigla, turma)
            if key_turma not in grouped:
                grouped[key_turma] = Turma(
                    sigla=sigla,
                    nome=(item.get("NomeAtividadeEnsino") or "").strip(),
                    turma=turma,
                )
            grouped[key_turma].encontros.append(
                Encontro(
                    dia_semana=_to_int(item.get("DiaSemana")),
                    hora_inicio=item.get("HoraInicio"),
                    hora_fim=item.get("HoraFim"),
                    campus=item.get("DenominacaoCampus"),
                    espaco=item.get("DenominacaoEspacoFisico"),
                    descricao_local=item.get("DescricaoLocal"),
                )
            )

        turmas = sorted(grouped.values(), key=lambda t: (t.sigla, t.turma))
        self._cache.set(
            key,
            [turma.model_dump(mode="json") for turma in turmas],
            ttl_seconds=60 * 60,
        )
        return turmas

    def _paginate(
        self,
        path: str,
        collection: str,
        params: dict[str, Any] | None = None,
    ):
        page = 1
        while True:
            query = {**(params or {}), "per-page": PER_PAGE, "page": page}
            data = self._get(path, query)
            yield from data.get(collection) or []
            page_count = int((data.get("_meta") or {}).get("pageCount") or 1)
            if page >= page_count:
                break
            page += 1

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=30)
        return self._client

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._http().get(f"{BASE_URL}{path}", params=params)
        except httpx.HTTPError as exc:
            raise ApiError(f"falha ao consultar {path}: {exc}") from exc

        if response.status_code != 200:
            raise ApiError(f"{path} respondeu HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiError(f"{path} não respondeu JSON") from exc

        if not payload.get("success", False):
            raise ApiError(f"{path} respondeu success={payload.get('success')!r}")
        return payload.get("data") or {}


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
