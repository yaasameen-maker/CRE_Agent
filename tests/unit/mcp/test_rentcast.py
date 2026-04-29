"""Tests for RentCast MCP server — get_rent_trend, get_vacancy_rate."""

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


def _markets_body() -> dict[str, object]:
    return {
        "zipCode": "10001",
        "averageRent": 3200.0,
        "medianRent": 3100.0,
        "minRent": 1800.0,
        "maxRent": 6500.0,
        "vacancyRate": 4.2,
        "rentChangePercentage": -2.1,
        "totalProperties": 5432,
    }


class TestFetchMarketsCache:
    def test_cache_hit_skips_api_call(self) -> None:
        cached = _markets_body()
        client = _mock_client({})
        with patch("src.mcp.rentcast.bronze_get", return_value=cached):
            with patch("src.mcp.rentcast.bronze_set") as mock_set:
                from src.mcp.rentcast import _fetch_markets

                result = _fetch_markets("10001", client=client)
                assert result == cached
                mock_set.assert_not_called()
                client.get.assert_not_called()

    def test_cache_miss_writes_bronze(self) -> None:
        api_body = _markets_body()
        with patch("src.mcp.rentcast.bronze_get", return_value=None):
            with patch("src.mcp.rentcast.bronze_set") as mock_set:
                with patch.dict(
                    os.environ,
                    {"RENTCAST_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.rentcast import _fetch_markets

                    _fetch_markets("10001", client=_mock_client(api_body))
                    mock_set.assert_called_once_with("rentcast", "10001", api_body)


class TestFetchMarketsRequest:
    def test_correct_url(self) -> None:
        client = _mock_client(_markets_body())
        with patch("src.mcp.rentcast.bronze_get", return_value=None):
            with patch("src.mcp.rentcast.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"RENTCAST_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.rentcast import _fetch_markets

                    _fetch_markets("10001", client=client)
        assert client.get.call_args[0][0] == "https://api.rentcast.io/v1/markets"

    def test_zip_in_params_and_api_key_in_header(self) -> None:
        client = _mock_client(_markets_body())
        with patch("src.mcp.rentcast.bronze_get", return_value=None):
            with patch("src.mcp.rentcast.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"RENTCAST_API_KEY": "my-rc-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.rentcast import _fetch_markets

                    _fetch_markets("10001", client=client)
        params = client.get.call_args[1]["params"]
        headers = client.get.call_args[1]["headers"]
        assert params["zipCode"] == "10001"
        assert headers["X-Api-Key"] == "my-rc-key"  # pragma: allowlist secret


class TestFetchMarketsErrors:
    def test_http_error_raises(self) -> None:
        with patch("src.mcp.rentcast.bronze_get", return_value=None):
            with patch.dict(
                os.environ,
                {"RENTCAST_API_KEY": "test-key"},  # pragma: allowlist secret
            ):
                from src.mcp.rentcast import _fetch_markets

                with pytest.raises(RuntimeError, match="403"):
                    _fetch_markets(
                        "10001",
                        client=_mock_client({"message": "Forbidden"}, status=403),
                    )

    def test_missing_api_key_raises(self) -> None:
        with patch("src.mcp.rentcast.bronze_get", return_value=None):
            clean = {k: v for k, v in os.environ.items() if k != "RENTCAST_API_KEY"}
            with patch.dict(os.environ, clean, clear=True):
                from src.mcp.rentcast import _fetch_markets

                with pytest.raises(ValueError, match="RENTCAST_API_KEY"):
                    _fetch_markets("10001", client=_mock_client({}))

    def test_transport_error_raises_runtime_error(self) -> None:
        client = _mock_client({})
        client.get.side_effect = httpx.ConnectError("connection refused")
        with patch("src.mcp.rentcast.bronze_get", return_value=None):
            with patch.dict(
                os.environ,
                {"RENTCAST_API_KEY": "test-key"},  # pragma: allowlist secret
            ):
                from src.mcp.rentcast import _fetch_markets

                with pytest.raises(RuntimeError, match="RentCast API request failed"):
                    _fetch_markets("10001", client=client)


class TestGetRentTrend:
    def test_returns_rent_fields(self) -> None:
        with patch("src.mcp.rentcast._fetch_markets", return_value=_markets_body()):
            from src.mcp.rentcast import get_rent_trend

            result = get_rent_trend("10001")
        assert result["zip_code"] == "10001"
        assert result["average_rent"] == 3200.0
        assert result["median_rent"] == 3100.0
        assert result["rent_change_percentage"] == -2.1


class TestGetVacancyRate:
    def test_returns_vacancy_field(self) -> None:
        with patch("src.mcp.rentcast._fetch_markets", return_value=_markets_body()):
            from src.mcp.rentcast import get_vacancy_rate

            result = get_vacancy_rate("10001")
        assert result["zip_code"] == "10001"
        assert result["vacancy_rate"] == 4.2
