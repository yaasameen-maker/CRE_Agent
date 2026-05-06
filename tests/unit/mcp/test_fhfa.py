"""Tests for FHFA MCP server — get_price_index."""

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


def _fhfa_body() -> dict[str, object]:
    return {
        "meta": {"metro_area": "C3562"},
        "data": [
            {"period": "2025Q1", "index_sa": 312.5},
            {"period": "2025Q2", "index_sa": 308.1},
        ],
    }


class TestFetchPriceIndexCache:
    def test_cache_hit_skips_api_call(self) -> None:
        cached = _fhfa_body()
        client = _mock_client({})
        with patch("src.mcp.fhfa.bronze_get", return_value=cached):
            with patch("src.mcp.fhfa.bronze_set") as mock_set:
                from src.mcp.fhfa import _fetch_price_index

                result = _fetch_price_index("C3562", client=client)
                assert result == cached
                mock_set.assert_not_called()
                client.get.assert_not_called()

    def test_cache_miss_writes_bronze(self) -> None:
        body = _fhfa_body()
        with patch("src.mcp.fhfa.bronze_get", return_value=None):
            with patch("src.mcp.fhfa.bronze_set") as mock_set:
                with patch.dict(
                    os.environ,
                    {"FHFA_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.fhfa import _fetch_price_index

                    _fetch_price_index("C3562", client=_mock_client(body))
                    mock_set.assert_called_once_with("fhfa", "price_index:C3562", body)


class TestFetchPriceIndexRequest:
    def test_metro_code_and_api_key_in_params(self) -> None:
        client = _mock_client(_fhfa_body())
        with patch("src.mcp.fhfa.bronze_get", return_value=None):
            with patch("src.mcp.fhfa.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"FHFA_API_KEY": "my-fhfa-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.fhfa import _fetch_price_index

                    _fetch_price_index("C3562", client=client)
        params = client.get.call_args[1]["params"]
        assert params["metro_area"] == "C3562"
        assert params["api_key"] == "my-fhfa-key"  # pragma: allowlist secret

    def test_returns_full_response(self) -> None:
        body = _fhfa_body()
        with patch("src.mcp.fhfa.bronze_get", return_value=None):
            with patch("src.mcp.fhfa.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"FHFA_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.fhfa import _fetch_price_index

                    result = _fetch_price_index("C3562", client=_mock_client(body))
        assert result == body


class TestFetchPriceIndexErrors:
    def test_missing_api_key_raises(self) -> None:
        with patch("src.mcp.fhfa.bronze_get", return_value=None):
            clean = {k: v for k, v in os.environ.items() if k != "FHFA_API_KEY"}
            with patch.dict(os.environ, clean, clear=True):
                from src.mcp.fhfa import _fetch_price_index

                with pytest.raises(ValueError, match="FHFA_API_KEY"):
                    _fetch_price_index("C3562", client=_mock_client({}))

    def test_http_error_raises(self) -> None:
        with patch("src.mcp.fhfa.bronze_get", return_value=None):
            with patch.dict(os.environ, {"FHFA_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.fhfa import _fetch_price_index

                with pytest.raises(RuntimeError, match="404"):
                    _fetch_price_index("C3562", client=_mock_client({}, status=404))

    def test_transport_error_raises_runtime_error(self) -> None:
        client = _mock_client({})
        client.get.side_effect = httpx.ConnectError("connection refused")
        with patch("src.mcp.fhfa.bronze_get", return_value=None):
            with patch.dict(os.environ, {"FHFA_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.fhfa import _fetch_price_index

                with pytest.raises(RuntimeError, match="FHFA API request failed"):
                    _fetch_price_index("C3562", client=client)


class TestGetPriceIndex:
    def test_delegates_to_fetch(self) -> None:
        expected = _fhfa_body()
        with patch("src.mcp.fhfa._fetch_price_index", return_value=expected) as mock_fetch:
            from src.mcp.fhfa import get_price_index

            result = get_price_index("C3562")
            assert result == expected
            mock_fetch.assert_called_once_with("C3562")
