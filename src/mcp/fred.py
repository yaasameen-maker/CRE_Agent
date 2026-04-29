"""FRED MCP server — get_delinquency_rate tool."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

import httpx
from strands.tools import tool

from src.mcp._db import bronze_get, bronze_set

_FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


@runtime_checkable
class _HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str]) -> Any: ...


def _fetch_delinquency_rate(
    series_id: str,
    client: _HttpClient | None = None,
) -> dict[str, object]:
    """Check Bronze → call FRED API → write Bronze → return observations dict.

    Raises:
        ValueError: If FRED_API_KEY is not set.
        RuntimeError: If the FRED API returns a non-2xx status.
    """
    cached = bronze_get("fred", series_id)
    if cached is not None:
        return cached

    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        raise ValueError(
            "FRED_API_KEY environment variable is required. "
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    params = {"series_id": series_id, "api_key": api_key, "file_type": "json"}
    try:
        if client is None:
            with httpx.Client(timeout=30.0) as _client:
                response = _client.get(_FRED_OBSERVATIONS_URL, params=params)
        else:
            response = client.get(_FRED_OBSERVATIONS_URL, params=params)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"FRED API request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"FRED API returned HTTP {response.status_code}: {response.text}")

    data: dict[str, object] = response.json()
    bronze_set("fred", series_id, data)
    return data


@tool
def get_delinquency_rate(series_id: str) -> dict[str, object]:
    """Fetch delinquency rate observations from FRED for the given series ID.

    Use series IDs like DRSREACBS (real estate loans), DRSFRMACBS (single-family
    residential), or DRCCLACBS (credit card) to retrieve quarterly delinquency rates.
    Returns the full FRED observations response including date and value pairs.
    Results are cached in Bronze — the API is not called twice for the same series.
    """
    return _fetch_delinquency_rate(series_id)
