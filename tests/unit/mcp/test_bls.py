"""Tests for BLS MCP server — get_employment_trend."""

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
    client.post.return_value = resp
    return client


def _bls_body(series_id: str = "LAUMT060310000000003") -> dict[str, object]:
    return {
        "status": "REQUEST_SUCCEEDED",
        "responseTime": 42,
        "Results": {
            "series": [
                {
                    "seriesID": series_id,
                    "data": [
                        {"year": "2025", "period": "M12", "periodName": "December", "value": "4.2"},
                        {"year": "2025", "period": "M11", "periodName": "November", "value": "4.4"},
                    ],
                }
            ]
        },
    }


class TestFetchEmploymentTrendCache:
    def test_cache_hit_skips_api_call(self) -> None:
        cached = _bls_body()
        client = _mock_client({})
        with patch("src.mcp.bls.bronze_get", return_value=cached):
            with patch("src.mcp.bls.bronze_set") as mock_set:
                from src.mcp.bls import _fetch_employment_trend

                result = _fetch_employment_trend("LAUMT060310000000003", client=client)
                assert result == cached
                mock_set.assert_not_called()
                client.post.assert_not_called()

    def test_cache_miss_writes_bronze(self) -> None:
        api_body = _bls_body()
        with patch("src.mcp.bls.bronze_get", return_value=None):
            with patch("src.mcp.bls.bronze_set") as mock_set:
                with patch.dict(
                    os.environ,
                    {"BLS_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.bls import _fetch_employment_trend

                    _fetch_employment_trend("LAUMT060310000000003", client=_mock_client(api_body))
                    mock_set.assert_called_once_with("bls", "LAUMT060310000000003", api_body)


class TestFetchEmploymentTrendRequest:
    def test_correct_url(self) -> None:
        client = _mock_client(_bls_body())
        with patch("src.mcp.bls.bronze_get", return_value=None):
            with patch("src.mcp.bls.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"BLS_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.bls import _fetch_employment_trend

                    _fetch_employment_trend("LAUMT060310000000003", client=client)
        assert client.post.call_args[0][0] == ("https://api.bls.gov/publicAPI/v2/timeseries/data/")

    def test_series_id_and_key_in_body(self) -> None:
        client = _mock_client(_bls_body())
        with patch("src.mcp.bls.bronze_get", return_value=None):
            with patch("src.mcp.bls.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"BLS_API_KEY": "my-bls-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.bls import _fetch_employment_trend

                    _fetch_employment_trend("LAUMT060310000000003", client=client)
        body = client.post.call_args[1]["json"]
        assert body["seriesid"] == ["LAUMT060310000000003"]
        assert body["registrationkey"] == "my-bls-key"  # pragma: allowlist secret

    def test_returns_full_response(self) -> None:
        body = _bls_body()
        with patch("src.mcp.bls.bronze_get", return_value=None):
            with patch("src.mcp.bls.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"BLS_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.bls import _fetch_employment_trend

                    result = _fetch_employment_trend(
                        "LAUMT060310000000003", client=_mock_client(body)
                    )
        assert result["Results"]["series"][0]["seriesID"] == "LAUMT060310000000003"  # type: ignore[index]


class TestFetchEmploymentTrendErrors:
    def test_missing_api_key_raises(self) -> None:
        with patch("src.mcp.bls.bronze_get", return_value=None):
            clean = {k: v for k, v in os.environ.items() if k != "BLS_API_KEY"}
            with patch.dict(os.environ, clean, clear=True):
                from src.mcp.bls import _fetch_employment_trend

                with pytest.raises(ValueError, match="BLS_API_KEY"):
                    _fetch_employment_trend("LAUMT060310000000003", client=_mock_client({}))

    def test_http_error_raises(self) -> None:
        with patch("src.mcp.bls.bronze_get", return_value=None):
            with patch.dict(os.environ, {"BLS_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.bls import _fetch_employment_trend

                with pytest.raises(RuntimeError, match="500"):
                    _fetch_employment_trend(
                        "LAUMT060310000000003",
                        client=_mock_client({"error": "server error"}, status=500),
                    )

    def test_transport_error_raises_runtime_error(self) -> None:
        client = _mock_client({})
        client.post.side_effect = httpx.ConnectError("connection refused")
        with patch("src.mcp.bls.bronze_get", return_value=None):
            with patch.dict(os.environ, {"BLS_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.bls import _fetch_employment_trend

                with pytest.raises(RuntimeError, match="BLS API request failed"):
                    _fetch_employment_trend("LAUMT060310000000003", client=client)

    def test_bls_api_failure_status_raises(self) -> None:
        error_body: dict[str, object] = {
            "status": "REQUEST_FAILED",
            "message": ["No data found."],
        }
        with patch("src.mcp.bls.bronze_get", return_value=None):
            with patch.dict(os.environ, {"BLS_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.bls import _fetch_employment_trend

                with pytest.raises(RuntimeError, match="REQUEST_FAILED"):
                    _fetch_employment_trend("LAUMT060310000000003", client=_mock_client(error_body))


class TestGetEmploymentTrend:
    def test_delegates_to_fetch(self) -> None:
        expected = _bls_body()
        with patch("src.mcp.bls._fetch_employment_trend", return_value=expected) as mock_fetch:
            from src.mcp.bls import get_employment_trend

            result = get_employment_trend("LAUMT060310000000003")
            assert result == expected
            mock_fetch.assert_called_once_with("LAUMT060310000000003")
