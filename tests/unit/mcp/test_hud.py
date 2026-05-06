"""Tests for HUD MCP server — get_hud_vacancy."""

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


def _hud_body() -> dict[str, object]:
    return {
        "data": {
            "results": [
                {"zip": "10001", "res_ratio": 0.034, "bus_ratio": 0.121},
                {"zip": "10002", "res_ratio": 0.041, "bus_ratio": 0.098},
            ]
        }
    }


class TestFetchHudVacancyCache:
    def test_cache_hit_skips_api_call(self) -> None:
        cached = _hud_body()
        client = _mock_client({})
        with patch("src.mcp.hud.bronze_get", return_value=cached):
            with patch("src.mcp.hud.bronze_set") as mock_set:
                from src.mcp.hud import _fetch_hud_vacancy

                result = _fetch_hud_vacancy("METRO35620M35620", client=client)
                assert result == cached
                mock_set.assert_not_called()
                client.get.assert_not_called()

    def test_cache_miss_writes_bronze(self) -> None:
        body = _hud_body()
        with patch("src.mcp.hud.bronze_get", return_value=None):
            with patch("src.mcp.hud.bronze_set") as mock_set:
                with patch.dict(
                    os.environ,
                    {"HUD_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.hud import _fetch_hud_vacancy

                    _fetch_hud_vacancy("METRO35620M35620", client=_mock_client(body))
                    mock_set.assert_called_once_with("hud", "hud_vacancy:METRO35620M35620", body)


class TestFetchHudVacancyRequest:
    def test_api_key_in_auth_header(self) -> None:
        client = _mock_client(_hud_body())
        with patch("src.mcp.hud.bronze_get", return_value=None):
            with patch("src.mcp.hud.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"HUD_API_KEY": "my-hud-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.hud import _fetch_hud_vacancy

                    _fetch_hud_vacancy("METRO35620M35620", client=client)
        headers = client.get.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer my-hud-key"  # pragma: allowlist secret

    def test_metro_code_in_params(self) -> None:
        client = _mock_client(_hud_body())
        with patch("src.mcp.hud.bronze_get", return_value=None):
            with patch("src.mcp.hud.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"HUD_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.hud import _fetch_hud_vacancy

                    _fetch_hud_vacancy("METRO35620M35620", client=client)
        params = client.get.call_args[1]["params"]
        assert params["query"] == "METRO35620M35620"

    def test_returns_full_response(self) -> None:
        body = _hud_body()
        with patch("src.mcp.hud.bronze_get", return_value=None):
            with patch("src.mcp.hud.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"HUD_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.hud import _fetch_hud_vacancy

                    result = _fetch_hud_vacancy("METRO35620M35620", client=_mock_client(body))
        assert result == body


class TestFetchHudVacancyErrors:
    def test_missing_api_key_raises(self) -> None:
        with patch("src.mcp.hud.bronze_get", return_value=None):
            clean = {k: v for k, v in os.environ.items() if k != "HUD_API_KEY"}
            with patch.dict(os.environ, clean, clear=True):
                from src.mcp.hud import _fetch_hud_vacancy

                with pytest.raises(ValueError, match="HUD_API_KEY"):
                    _fetch_hud_vacancy("METRO35620M35620", client=_mock_client({}))

    def test_http_error_raises(self) -> None:
        with patch("src.mcp.hud.bronze_get", return_value=None):
            with patch.dict(os.environ, {"HUD_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.hud import _fetch_hud_vacancy

                with pytest.raises(RuntimeError, match="500"):
                    _fetch_hud_vacancy(
                        "METRO35620M35620",
                        client=_mock_client({}, status=500),
                    )

    def test_transport_error_raises_runtime_error(self) -> None:
        client = _mock_client({})
        client.get.side_effect = httpx.ConnectError("connection refused")
        with patch("src.mcp.hud.bronze_get", return_value=None):
            with patch.dict(os.environ, {"HUD_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.hud import _fetch_hud_vacancy

                with pytest.raises(RuntimeError, match="HUD API request failed"):
                    _fetch_hud_vacancy("METRO35620M35620", client=client)


class TestGetHudVacancy:
    def test_delegates_to_fetch(self) -> None:
        expected = _hud_body()
        with patch("src.mcp.hud._fetch_hud_vacancy", return_value=expected) as mock_fetch:
            from src.mcp.hud import get_hud_vacancy

            result = get_hud_vacancy("METRO35620M35620")
            assert result == expected
            mock_fetch.assert_called_once_with("METRO35620M35620")
