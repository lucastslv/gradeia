"""Persistência das análises, sem dados pessoais."""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path

from pydantic import BaseModel

from ..core.models import Analise


class Mensagem(BaseModel):
    role: str
    content: str


class AnalysisStore:
    """Guarda a análise (curso, período e disciplinas) por id."""

    def __init__(self, path: str | Path = ".cache/analises.db") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analises (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS mensagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analise_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self._connection.commit()

    def save(self, analise: Analise, analise_id: str | None = None) -> str:
        analise_id = analise_id or uuid.uuid4().hex
        payload = analise.model_dump_json()
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO analises (id, payload, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (analise_id, payload, time.time()),
            )
            self._connection.commit()
        return analise_id

    def get(self, analise_id: str) -> Analise | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM analises WHERE id = ?", (analise_id,)
            ).fetchone()
        if row is None:
            return None
        return Analise.model_validate_json(row[0])

    def add_message(self, analise_id: str, role: str, content: str) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO mensagens (analise_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (analise_id, role, content, time.time()),
            )
            self._connection.commit()

    def messages(self, analise_id: str, limit: int = 20) -> list[Mensagem]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT role, content FROM mensagens
                WHERE analise_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (analise_id, limit),
            ).fetchall()
        return [Mensagem(role=role, content=content) for role, content in reversed(rows)]
