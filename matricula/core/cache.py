"""Cache simples com TTL. SQLite para persistir entre execuções."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Protocol


class Cache(Protocol):
    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...


class NullCache:
    """Cache desligado, usado em testes."""

    def get(self, key: str) -> Any | None:
        return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        return None


class SqliteCache:
    """Cache chave-valor em JSON, com expiração por chave."""

    def __init__(self, path: str | Path = ".cache/matricula.db") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at REAL NOT NULL
            )
            """
        )
        self._connection.commit()

    def get(self, key: str) -> Any | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None or row[1] < time.time():
            return None
        return json.loads(row[0])

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        payload = json.dumps(value, ensure_ascii=False)
        with self._lock:
            self._connection.execute(
                "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                (key, payload, time.time() + ttl_seconds),
            )
            self._connection.commit()
