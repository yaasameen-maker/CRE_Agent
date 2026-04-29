"""Tests for FRED MCP server — get_delinquency_rate."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import httpx
import pytest


def _mock_client(body: dict[str, object], status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.text = json.dumps(body)
    resp.json.return_value = body
    client = MagicMock()
    client.get.return_value = resp
    return client


def _fred_body() -> dict[str, object]:
    return {
        "realtime_start": "2025-01-01",
        "realtime_end": "2025-12-31",
        "observations": [
            {"date": "2025-07-01", "value": "2.38"},
            {"date": "2025-10-01", "value": "2.45"},
        ],
    }


class TestFetchDelinquencyRateCache:
    def test_cache_hit_skips_api_call(self) -> None:
        cached = _fred_body()
        client = _mock_client({})
        with patch("src.mcp.fred.bronze_get", return_value=cached):
            with patch("src.mcp.fred.bronze_set") as mock_set:
                from src.mcp.fred import _fetch_delinquency_rate

                result = _fetch_delinquency_rate("DRSREACBS", client=client)
                assert result == cached
                mock_set.assert_not_called()
                client.get.assert_not_called()

    def test_cache_miss_writes_bronze(self) -> None:
        api_body = _fred_body()
        with patch("src.mcp.fred.bronze_get", return_value=None):
            with patch("src.mcp.fred.bronze_set") as mock_set:
                with patch.dict(
                    os.environ,
                    {"FRED_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.fred import _fetch_delinquency_rate

                    _fetch_delinquency_rate("DRSREACBS", client=_mock_client(api_body))
                    mock_set.assert_called_once_with("fred", "DRSREACBS", api_body)


class TestFetchDelinquencyRateRequest:
    def test_correct_url(self) -> None:
        client = _mock_client(_fred_body())
        with patch("src.mcp.fred.bronze_get", return_value=None):
            with patch("src.mcp.fred.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"FRED_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.fred import _fetch_delinquency_rate

                    _fetch_delinquency_rate("DRSREACBS", client=client)
        assert client.get.call_args[0][0] == ("https://api.stlouisfed.org/fred/series/observations")

    def test_series_id_and_api_key_in_params(self) -> None:
        client = _mock_client(_fred_body())
        with patch("src.mcp.fred.bronze_get", return_value=None):
            with patch("src.mcp.fred.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"FRED_API_KEY": "my-fred-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.fred import _fetch_delinquency_rate

                    _fetch_delinquency_rate("DRSREACBS", client=client)
        params = client.get.call_args[1]["params"]
        assert params["series_id"] == "DRSREACBS"
        assert params["api_key"] == "my-fred-key"  # pragma: allowlist secret
        assert params["file_type"] == "json"

    def test_returns_full_response(self) -> None:
        body = _fred_body()
        with patch("src.mcp.fred.bronze_get", return_value=None):
            with patch("src.mcp.fred.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"FRED_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.fred import _fetch_delinquency_rate

                    result = _fetch_delinquency_rate("DRSREACBS", client=_mock_client(body))
        assert result["observations"] == body["observations"]


class TestFetchDelinquencyRateErrors:
    def test_missing_api_key_raises(self) -> None:
        with patch("src.mcp.fred.bronze_get", return_value=None):
            clean = {k: v for k, v in os.environ.items() if k != "FRED_API_KEY"}
            with patch.dict(os.environ, clean, clear=True):
                from src.mcp.fred import _fetch_delinquency_rate

                with pytest.raises(ValueError, match="FRED_API_KEY"):
                    _fetch_delinquency_rate("DRSREACBS", client=_mock_client({}))

    def test_http_error_raises(self) -> None:
        with patch("src.mcp.fred.bronze_get", return_value=None):
            with patch.dict(os.environ, {"FRED_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.fred import _fetch_delinquency_rate

                with pytest.raises(RuntimeError, match="429"):
                    _fetch_delinquency_rate(
                        "DRSREACBS",
                        client=_mock_client({"error": "rate limited"}, status=429),
                    )

    def test_transport_error_raises_runtime_error(self) -> None:
        client = _mock_client({})
        client.get.side_effect = httpx.ConnectError("connection refused")
        with patch("src.mcp.fred.bronze_get", return_value=None):
            with patch.dict(os.environ, {"FRED_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.fred import _fetch_delinquency_rate

                with pytest.raises(RuntimeError, match="FRED API request failed"):
                    _fetch_delinquency_rate("DRSREACBS", client=client)


class TestGetDelinquencyRate:
    def test_delegates_to_fetch(self) -> None:
        expected = _fred_body()
        with patch("src.mcp.fred._fetch_delinquency_rate", return_value=expected) as mock_fetch:
            from src.mcp.fred import get_delinquency_rate

            result = get_delinquency_rate("DRSREACBS")
            assert result == expected
            mock_fetch.assert_called_once_with("DRSREACBS")
