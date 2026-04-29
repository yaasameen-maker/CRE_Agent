"""RentCast MCP server — get_rent_trend and get_vacancy_rate tools."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

import httpx
from strands.tools import tool

from src.mcp._db import bronze_get, bronze_set

_RENTCAST_MARKETS_URL = "https://api.rentcast.io/v1/markets"


@runtime_checkable
class _HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> Any: ...


def _fetch_markets(
    zip_code: str,
    client: _HttpClient | None = None,
) -> dict[str, object]:
    """Check Bronze → call RentCast markets API → write Bronze → return markets dict.

    Shared by get_rent_trend and get_vacancy_rate to preserve the 50 calls/month quota.

    Raises:
        ValueError: If RENTCAST_API_KEY is not set.
        RuntimeError: If the RentCast API returns a non-2xx status.
    """
    cached = bronze_get("rentcast", zip_code)
    if cached is not None:
        return cached

    api_key = os.environ.get("RENTCAST_API_KEY", "")
    if not api_key:
        raise ValueError(
            "RENTCAST_API_KEY environment variable is required. "
            "Get one at https://app.rentcast.io/app/api-keys"
        )

    params = {"zipCode": zip_code}
    headers = {"X-Api-Key": api_key}
    try:
        if client is None:
            with httpx.Client(timeout=30.0) as _client:
                response = _client.get(_RENTCAST_MARKETS_URL, params=params, headers=headers)
        else:
            response = client.get(_RENTCAST_MARKETS_URL, params=params, headers=headers)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"RentCast API request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"RentCast API returned HTTP {response.status_code}: {response.text}")

    data: dict[str, object] = response.json()
    bronze_set("rentcast", zip_code, data)
    return data


@tool
def get_rent_trend(zip_code: str) -> dict[str, object]:
    """Fetch rent trend data from RentCast for the given ZIP code.

    Returns average rent, median rent, and 30-day rent change percentage.
    Results are cached in Bronze — only one API call per ZIP per run.
    """
    markets = _fetch_markets(zip_code)
    return {
        "zip_code": zip_code,
        "average_rent": markets.get("averageRent"),
        "median_rent": markets.get("medianRent"),
        "rent_change_percentage": markets.get("rentChangePercentage"),
    }


@tool
def get_vacancy_rate(zip_code: str) -> dict[str, object]:
    """Fetch vacancy rate from RentCast for the given ZIP code.

    Returns the current vacancy rate as a percentage.
    Shares the Bronze cache entry with get_rent_trend to preserve API quota.
    """
    markets = _fetch_markets(zip_code)
    return {
        "zip_code": zip_code,
        "vacancy_rate": markets.get("vacancyRate"),
    }
