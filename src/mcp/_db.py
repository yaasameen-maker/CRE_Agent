"""Bronze layer SQLite helpers — cache-first access for every MCP tool."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime

_DEFAULT_DB_PATH = "data/cre_signal.db"


def _get_conn() -> sqlite3.Connection:
    """Return a SQLite connection, creating the Bronze schema if absent."""
    path = os.getenv("CRE_DB_PATH", _DEFAULT_DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bronze_cache (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            source        TEXT    NOT NULL,
            cache_key     TEXT    NOT NULL,
            response_json TEXT    NOT NULL,
            fetched_at    TEXT    NOT NULL
        )
    """)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_bronze_source_key ON bronze_cache(source, cache_key)"
    )
    conn.commit()
    return conn


def bronze_get(source: str, cache_key: str) -> dict[str, object] | None:
    """Return the cached API response for *source*+*cache_key*, or None on miss."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT response_json FROM bronze_cache WHERE source = ? AND cache_key = ?",
        (source, cache_key),
    ).fetchone()
    conn.close()
    return json.loads(row["response_json"]) if row else None


def bronze_set(source: str, cache_key: str, data: dict[str, object]) -> None:
    """Write *data* to Bronze, replacing any existing entry for *source*+*cache_key*."""
    now = datetime.now(UTC).isoformat()
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO bronze_cache (source, cache_key, response_json, fetched_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source, cache_key) DO UPDATE SET
                response_json = excluded.response_json,
                fetched_at    = excluded.fetched_at
            """,
            (source, cache_key, json.dumps(data), now),
        )
        conn.commit()
    finally:
        conn.close()
