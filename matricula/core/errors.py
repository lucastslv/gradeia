"""Erros de domínio do assistente de matrícula."""


class MatriculaError(Exception):
    """Erro base do domínio."""


class ParseError(MatriculaError):
    """O HTML enviado não tem o formato esperado."""


class ApiError(MatriculaError):
    """A API da UFRGS respondeu de forma inesperada."""


class CourseNotFound(MatriculaError):
    """Não foi possível resolver o curso informado no arquivo."""


class AmbiguousCourse(MatriculaError):
    """O nome do curso resolve para mais de um identificador."""

    def __init__(self, nome: str, identificadores: list[str]) -> None:
        self.nome = nome
        self.identificadores = identificadores
        super().__init__(
            f"curso {nome!r} resolve para múltiplos identificadores: "
            f"{', '.join(identificadores)}"
        )
