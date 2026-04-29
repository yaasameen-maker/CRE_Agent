"""BLS MCP server — get_employment_trend tool."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

import httpx
from strands.tools import tool

from src.mcp._db import bronze_get, bronze_set

_BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


@runtime_checkable
class _HttpClient(Protocol):
    def post(self, url: str, *, json: dict[str, object], headers: dict[str, str]) -> Any: ...


def _fetch_employment_trend(
    metro_code: str,
    client: _HttpClient | None = None,
) -> dict[str, object]:
    """Check Bronze → call BLS API → write Bronze → return series data.

    Raises:
        ValueError: If BLS_API_KEY is not set.
        RuntimeError: If the BLS API returns a non-2xx status or REQUEST_FAILED body.
    """
    cached = bronze_get("bls", metro_code)
    if cached is not None:
        return cached

    api_key = os.environ.get("BLS_API_KEY", "")
    if not api_key:
        raise ValueError(
            "BLS_API_KEY environment variable is required. "
            "Register free at https://data.bls.gov/registrationEngine/"
        )

    body: dict[str, object] = {"seriesid": [metro_code], "registrationkey": api_key}
    headers = {"Content-Type": "application/json"}
    try:
        if client is None:
            with httpx.Client(timeout=30.0) as _client:
                response = _client.post(_BLS_URL, json=body, headers=headers)
        else:
            response = client.post(_BLS_URL, json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"BLS API request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"BLS API returned HTTP {response.status_code}: {response.text}")

    data: dict[str, object] = response.json()
    if data.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS API returned status {data.get('status')!r}: {data}")

    bronze_set("bls", metro_code, data)
    return data


@tool
def get_employment_trend(metro_code: str) -> dict[str, object]:
    """Fetch employment trend data from BLS for the given metro area series ID.

    metro_code is a full BLS LAUS series ID, e.g. LAUMT060310000000003 for the
    Los Angeles metro unemployment rate. Returns the BLS timeseries response with
    monthly data ordered most-recent-first.
    Results are cached in Bronze — the API is not called twice for the same metro.
    """
    return _fetch_employment_trend(metro_code)
