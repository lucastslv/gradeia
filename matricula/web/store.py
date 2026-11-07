"""Persistência das análises, sem dados pessoais."""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path

from ..core.models import Analise


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
