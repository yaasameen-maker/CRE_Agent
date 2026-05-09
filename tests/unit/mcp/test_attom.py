"""Tests for ATTOM MCP server — get_foreclosure_filings and get_deed_transfers."""

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


def _attom_body() -> dict[str, object]:
    return {
        "status": {"version": "1.0.0", "code": 0, "msg": "SuccessWithResult"},
        "property": [
            {"identifier": {"Id": 1234}, "address": {"postal1": "10001"}},
        ],
    }


# ─── Foreclosure filings ──────────────────────────────────────────────────────


class TestFetchForeclosureCacheHit:
    def test_cache_hit_skips_api_call(self) -> None:
        cached = _attom_body()
        client = _mock_client({})
        with patch("src.mcp.attom.bronze_get", return_value=cached):
            with patch("src.mcp.attom.bronze_set") as mock_set:
                from src.mcp.attom import _fetch_foreclosure_filings

                result = _fetch_foreclosure_filings("10001", client=client)
                assert result == cached
                mock_set.assert_not_called()
                client.get.assert_not_called()

    def test_cache_key_includes_zip_and_days(self) -> None:
        with patch("src.mcp.attom.bronze_get", return_value=None):
            with patch("src.mcp.attom.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"ATTOM_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.attom import _fetch_foreclosure_filings

                    _fetch_foreclosure_filings(
                        "10001", days_back=30, client=_mock_client(_attom_body())
                    )

        with patch("src.mcp.attom.bronze_get") as mock_get:
            mock_get.return_value = None
            with patch("src.mcp.attom.bronze_set") as mock_set:
                with patch.dict(
                    os.environ,
                    {"ATTOM_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.attom import _fetch_foreclosure_filings

                    _fetch_foreclosure_filings(
                        "10001", days_back=30, client=_mock_client(_attom_body())
                    )
                    mock_get.assert_called_with("attom", "foreclosures:10001:30")
                    mock_set.assert_called_once_with(
                        "attom", "foreclosures:10001:30", _attom_body()
                    )


class TestFetchForeclosureCacheMiss:
    def test_cache_miss_writes_bronze(self) -> None:
        body = _attom_body()
        with patch("src.mcp.attom.bronze_get", return_value=None):
            with patch("src.mcp.attom.bronze_set") as mock_set:
                with patch.dict(
                    os.environ,
                    {"ATTOM_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.attom import _fetch_foreclosure_filings

                    _fetch_foreclosure_filings("10001", client=_mock_client(body))
                    mock_set.assert_called_once_with("attom", "foreclosures:10001:90", body)


class TestFetchForeclosureRequest:
    def test_api_key_sent_in_header(self) -> None:
        client = _mock_client(_attom_body())
        with patch("src.mcp.attom.bronze_get", return_value=None):
            with patch("src.mcp.attom.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"ATTOM_API_KEY": "my-attom-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.attom import _fetch_foreclosure_filings

                    _fetch_foreclosure_filings("10001", client=client)
        headers = client.get.call_args[1]["headers"]
        assert headers["apikey"] == "my-attom-key"  # pragma: allowlist secret

    def test_zip_code_in_params(self) -> None:
        client = _mock_client(_attom_body())
        with patch("src.mcp.attom.bronze_get", return_value=None):
            with patch("src.mcp.attom.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"ATTOM_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.attom import _fetch_foreclosure_filings

                    _fetch_foreclosure_filings("10001", client=client)
        params = client.get.call_args[1]["params"]
        assert params["postalcode"] == "10001"

    def test_returns_full_response(self) -> None:
        body = _attom_body()
        with patch("src.mcp.attom.bronze_get", return_value=None):
            with patch("src.mcp.attom.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"ATTOM_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.attom import _fetch_foreclosure_filings

                    result = _fetch_foreclosure_filings("10001", client=_mock_client(body))
        assert result == body


class TestFetchForeclosureErrors:
    def test_missing_api_key_returns_empty(self) -> None:
        with patch("src.mcp.attom.bronze_get", return_value=None):
            clean = {k: v for k, v in os.environ.items() if k != "ATTOM_API_KEY"}
            with patch.dict(os.environ, clean, clear=True):
                from src.mcp.attom import _fetch_foreclosure_filings

                result = _fetch_foreclosure_filings("10001", client=_mock_client({}))
                assert result == {}

    def test_http_error_raises(self) -> None:
        with patch("src.mcp.attom.bronze_get", return_value=None):
            with patch.dict(os.environ, {"ATTOM_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.attom import _fetch_foreclosure_filings

                with pytest.raises(RuntimeError, match="429"):
                    _fetch_foreclosure_filings(
                        "10001",
                        client=_mock_client({"error": "rate limited"}, status=429),
                    )

    def test_transport_error_raises_runtime_error(self) -> None:
        client = _mock_client({})
        client.get.side_effect = httpx.ConnectError("connection refused")
        with patch("src.mcp.attom.bronze_get", return_value=None):
            with patch.dict(os.environ, {"ATTOM_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.attom import _fetch_foreclosure_filings

                with pytest.raises(RuntimeError, match="ATTOM API request failed"):
                    _fetch_foreclosure_filings("10001", client=client)


# ─── Deed transfers ───────────────────────────────────────────────────────────


class TestFetchDeedCacheHit:
    def test_cache_hit_skips_api_call(self) -> None:
        cached = _attom_body()
        client = _mock_client({})
        with patch("src.mcp.attom.bronze_get", return_value=cached):
            with patch("src.mcp.attom.bronze_set") as mock_set:
                from src.mcp.attom import _fetch_deed_transfers

                result = _fetch_deed_transfers("10001", client=client)
                assert result == cached
                mock_set.assert_not_called()
                client.get.assert_not_called()


class TestFetchDeedCacheMiss:
    def test_cache_miss_writes_bronze(self) -> None:
        body = _attom_body()
        with patch("src.mcp.attom.bronze_get", return_value=None):
            with patch("src.mcp.attom.bronze_set") as mock_set:
                with patch.dict(
                    os.environ,
                    {"ATTOM_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.attom import _fetch_deed_transfers

                    _fetch_deed_transfers("10001", client=_mock_client(body))
                    mock_set.assert_called_once_with("attom", "deeds:10001:90", body)

    def test_cache_key_uses_deeds_prefix(self) -> None:
        with patch("src.mcp.attom.bronze_get") as mock_get:
            mock_get.return_value = None
            with patch("src.mcp.attom.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"ATTOM_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.attom import _fetch_deed_transfers

                    _fetch_deed_transfers("10001", days_back=45, client=_mock_client(_attom_body()))
                    mock_get.assert_called_with("attom", "deeds:10001:45")


class TestFetchDeedErrors:
    def test_missing_api_key_returns_empty(self) -> None:
        with patch("src.mcp.attom.bronze_get", return_value=None):
            clean = {k: v for k, v in os.environ.items() if k != "ATTOM_API_KEY"}
            with patch.dict(os.environ, clean, clear=True):
                from src.mcp.attom import _fetch_deed_transfers

                result = _fetch_deed_transfers("10001", client=_mock_client({}))
                assert result == {}

    def test_http_error_raises(self) -> None:
        with patch("src.mcp.attom.bronze_get", return_value=None):
            with patch.dict(os.environ, {"ATTOM_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.attom import _fetch_deed_transfers

                with pytest.raises(RuntimeError, match="503"):
                    _fetch_deed_transfers(
                        "10001",
                        client=_mock_client({}, status=503),
                    )

    def test_transport_error_raises_runtime_error(self) -> None:
        client = _mock_client({})
        client.get.side_effect = httpx.ConnectError("connection refused")
        with patch("src.mcp.attom.bronze_get", return_value=None):
            with patch.dict(os.environ, {"ATTOM_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.attom import _fetch_deed_transfers

                with pytest.raises(RuntimeError, match="ATTOM API request failed"):
                    _fetch_deed_transfers("10001", client=client)


# ─── Public tool delegates ────────────────────────────────────────────────────


class TestGetForeclosureFilings:
    def test_delegates_to_fetch(self) -> None:
        expected = _attom_body()
        with patch("src.mcp.attom._fetch_foreclosure_filings", return_value=expected) as mock_fetch:
            from src.mcp.attom import get_foreclosure_filings

            result = get_foreclosure_filings("10001")
            assert result == expected
            mock_fetch.assert_called_once_with("10001", 90)


class TestGetDeedTransfers:
    def test_delegates_to_fetch(self) -> None:
        expected = _attom_body()
        with patch("src.mcp.attom._fetch_deed_transfers", return_value=expected) as mock_fetch:
            from src.mcp.attom import get_deed_transfers

            result = get_deed_transfers("10001")
            assert result == expected
            mock_fetch.assert_called_once_with("10001", 90)
