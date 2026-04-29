"""Tests for Bronze layer SQLite helpers."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch


def _make_temp_db() -> str:
    """Create an empty temp file for use as a SQLite test database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


class TestBronzeGet:
    def test_miss_returns_none(self) -> None:
        path = _make_temp_db()
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                from src.mcp._db import bronze_get

                assert bronze_get("fred", "DRSREACBS") is None
        finally:
            os.unlink(path)

    def test_hit_returns_dict(self) -> None:
        path = _make_temp_db()
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                from src.mcp._db import bronze_get, bronze_set

                bronze_set("fred", "DRSREACBS", {"observations": [{"value": "2.5"}]})
                result = bronze_get("fred", "DRSREACBS")
                assert result == {"observations": [{"value": "2.5"}]}
        finally:
            os.unlink(path)

    def test_different_sources_isolated(self) -> None:
        path = _make_temp_db()
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                from src.mcp._db import bronze_get, bronze_set

                bronze_set("fred", "KEY_A", {"v": 1})
                assert bronze_get("bls", "KEY_A") is None
        finally:
            os.unlink(path)

    def test_different_keys_isolated(self) -> None:
        path = _make_temp_db()
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                from src.mcp._db import bronze_get, bronze_set

                bronze_set("fred", "KEY_A", {"v": 1})
                assert bronze_get("fred", "KEY_B") is None
        finally:
            os.unlink(path)


class TestBronzeSet:
    def test_roundtrip(self) -> None:
        path = _make_temp_db()
        data = {"observations": [{"date": "2025-01-01", "value": "3.1"}]}
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                from src.mcp._db import bronze_get, bronze_set

                bronze_set("bls", "LAUMT123", data)
                assert bronze_get("bls", "LAUMT123") == data
        finally:
            os.unlink(path)

    def test_overwrite_replaces_existing(self) -> None:
        path = _make_temp_db()
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                from src.mcp._db import bronze_get, bronze_set

                bronze_set("rentcast", "10001", {"averageRent": 3000.0})
                bronze_set("rentcast", "10001", {"averageRent": 3200.0})
                result = bronze_get("rentcast", "10001")
                assert result == {"averageRent": 3200.0}
        finally:
            os.unlink(path)
