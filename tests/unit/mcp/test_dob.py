"""Tests for NYC DOB MCP — _fetch_dob_violations."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest


def _mock_client(body: list, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.text = json.dumps(body)
    resp.json.return_value = body
    client = MagicMock()
    client.get.return_value = resp
    return client


def _violation() -> dict:
    return {
        "violation_number": "V1234",
        "zip_code": "10001",
        "issue_date": "2026-04-01T00:00:00",
        "violation_type": "CONSTRUCTION",
        "description": "Illegal construction",
    }


class TestFetchDobViolationsCacheHit:
    def test_returns_cached_without_api_call(self) -> None:
        cached = {"records": [_violation()], "days_back": 90}
        with patch("src.mcp.dob.bronze_get", return_value=cached):
            with patch("src.mcp.dob.bronze_set") as mock_set:
                from src.mcp.dob import _fetch_dob_violations

                client = _mock_client([])
                result = _fetch_dob_violations("10001", client=client)
                assert result == cached
                mock_set.assert_not_called()
                client.get.assert_not_called()

    def test_cache_key_includes_zip_and_days(self) -> None:
        with patch("src.mcp.dob.bronze_get") as mock_get:
            mock_get.return_value = None
            with patch("src.mcp.dob.bronze_set"):
                from src.mcp.dob import _fetch_dob_violations

                _fetch_dob_violations("10036", days_back=60, client=_mock_client([]))
                mock_get.assert_called_with("dob", "violations:10036:60")


class TestFetchDobViolationsCacheMiss:
    def test_writes_response_to_bronze(self) -> None:
        violations = [_violation(), _violation()]
        with patch("src.mcp.dob.bronze_get", return_value=None):
            with patch("src.mcp.dob.bronze_set") as mock_set:
                from src.mcp.dob import _fetch_dob_violations

                _fetch_dob_violations("10001", client=_mock_client(violations))
                mock_set.assert_called_once()
                source, key, data = mock_set.call_args[0]
                assert source == "dob"
                assert key == "violations:10001:90"
                assert len(data["records"]) == 2

    def test_returns_records_and_days_back(self) -> None:
        with patch("src.mcp.dob.bronze_get", return_value=None):
            with patch("src.mcp.dob.bronze_set"):
                from src.mcp.dob import _fetch_dob_violations

                result = _fetch_dob_violations("10001", days_back=30, client=_mock_client([_violation()]))
                assert result["days_back"] == 30
                assert len(result["records"]) == 1  # type: ignore[arg-type]

    def test_http_error_raises(self) -> None:
        with patch("src.mcp.dob.bronze_get", return_value=None):
            from src.mcp.dob import _fetch_dob_violations

            with pytest.raises(RuntimeError, match="429"):
                _fetch_dob_violations(
                    "10001",
                    client=_mock_client([], status=429),
                )

    def test_transport_error_raises_runtime_error(self) -> None:
        client = MagicMock()
        client.get.side_effect = httpx.ConnectError("refused")
        with patch("src.mcp.dob.bronze_get", return_value=None):
            from src.mcp.dob import _fetch_dob_violations

            with pytest.raises(RuntimeError, match="DOB API request failed"):
                _fetch_dob_violations("10001", client=client)

    def test_query_includes_zip_and_date_filter(self) -> None:
        client = _mock_client([])
        with patch("src.mcp.dob.bronze_get", return_value=None):
            with patch("src.mcp.dob.bronze_set"):
                from src.mcp.dob import _fetch_dob_violations

                _fetch_dob_violations("10128", client=client)
        params = client.get.call_args[1]["params"]
        assert "10128" in params["$where"]
        assert "issue_date" in params["$where"]


class TestGetDobViolationsTool:
    def test_delegates_to_fetch(self) -> None:
        expected = {"records": [], "days_back": 90}
        with patch("src.mcp.dob._fetch_dob_violations", return_value=expected) as mock_fetch:
            from src.mcp.dob import get_dob_violations

            result = get_dob_violations("10001")
            assert result == expected
            mock_fetch.assert_called_once_with("10001")
