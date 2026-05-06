"""Tests for Census ACS MCP server — get_demographics."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import httpx
import pytest


def _mock_client(body: object, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.text = json.dumps(body)
    resp.json.return_value = body
    client = MagicMock()
    client.get.return_value = resp
    return client


def _census_raw() -> list[list[str]]:
    return [
        [
            "B19013_001E",
            "B25002_002E",
            "B25002_003E",
            "B23025_005E",
            "B23025_002E",
            "state",
            "county",
            "tract",
        ],
        ["72000", "1500", "80", "120", "2200", "36", "061", "009900"],
    ]


def _census_dict() -> dict[str, object]:
    headers, values = _census_raw()
    return dict(zip(headers, values, strict=False))


class TestFetchDemographicsCache:
    def test_cache_hit_skips_api_call(self) -> None:
        cached = _census_dict()
        client = _mock_client([])
        with patch("src.mcp.census.bronze_get", return_value=cached):
            with patch("src.mcp.census.bronze_set") as mock_set:
                from src.mcp.census import _fetch_demographics

                result = _fetch_demographics("36061009900", client=client)
                assert result == cached
                mock_set.assert_not_called()
                client.get.assert_not_called()

    def test_cache_miss_writes_bronze(self) -> None:
        with patch("src.mcp.census.bronze_get", return_value=None):
            with patch("src.mcp.census.bronze_set") as mock_set:
                with patch.dict(
                    os.environ,
                    {"CENSUS_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.census import _fetch_demographics

                    _fetch_demographics("36061009900", client=_mock_client(_census_raw()))
                    mock_set.assert_called_once_with(
                        "census",
                        "demographics:36061009900",
                        _census_dict(),
                    )


class TestFetchDemographicsRequest:
    def test_api_key_in_params(self) -> None:
        client = _mock_client(_census_raw())
        with patch("src.mcp.census.bronze_get", return_value=None):
            with patch("src.mcp.census.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"CENSUS_API_KEY": "my-census-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.census import _fetch_demographics

                    _fetch_demographics("36061009900", client=client)
        params = client.get.call_args[1]["params"]
        assert params["key"] == "my-census-key"  # pragma: allowlist secret

    def test_fips_parsed_into_params(self) -> None:
        client = _mock_client(_census_raw())
        with patch("src.mcp.census.bronze_get", return_value=None):
            with patch("src.mcp.census.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"CENSUS_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.census import _fetch_demographics

                    _fetch_demographics("36061009900", client=client)
        params = client.get.call_args[1]["params"]
        assert "36" in params["in"]
        assert "061" in params["in"]
        assert params["for"] == "tract:009900"

    def test_returns_dict_not_raw_list(self) -> None:
        with patch("src.mcp.census.bronze_get", return_value=None):
            with patch("src.mcp.census.bronze_set"):
                with patch.dict(
                    os.environ,
                    {"CENSUS_API_KEY": "test-key"},  # pragma: allowlist secret
                ):
                    from src.mcp.census import _fetch_demographics

                    result = _fetch_demographics("36061009900", client=_mock_client(_census_raw()))
        assert isinstance(result, dict)
        assert "B19013_001E" in result


class TestFetchDemographicsErrors:
    def test_missing_api_key_raises(self) -> None:
        with patch("src.mcp.census.bronze_get", return_value=None):
            clean = {k: v for k, v in os.environ.items() if k != "CENSUS_API_KEY"}
            with patch.dict(os.environ, clean, clear=True):
                from src.mcp.census import _fetch_demographics

                with pytest.raises(ValueError, match="CENSUS_API_KEY"):
                    _fetch_demographics("36061009900", client=_mock_client([]))

    def test_http_error_raises(self) -> None:
        with patch("src.mcp.census.bronze_get", return_value=None):
            with patch.dict(os.environ, {"CENSUS_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.census import _fetch_demographics

                with pytest.raises(RuntimeError, match="400"):
                    _fetch_demographics("36061009900", client=_mock_client([], status=400))

    def test_transport_error_raises_runtime_error(self) -> None:
        client = _mock_client([])
        client.get.side_effect = httpx.ConnectError("connection refused")
        with patch("src.mcp.census.bronze_get", return_value=None):
            with patch.dict(os.environ, {"CENSUS_API_KEY": "test-key"}):  # pragma: allowlist secret
                from src.mcp.census import _fetch_demographics

                with pytest.raises(RuntimeError, match="Census API request failed"):
                    _fetch_demographics("36061009900", client=client)


class TestGetDemographics:
    def test_delegates_to_fetch(self) -> None:
        expected = _census_dict()
        with patch("src.mcp.census._fetch_demographics", return_value=expected) as mock_fetch:
            from src.mcp.census import get_demographics

            result = get_demographics("36061009900")
            assert result == expected
            mock_fetch.assert_called_once_with("36061009900")
