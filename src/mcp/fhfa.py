"""FHFA MCP server — get_price_index tool."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

import httpx
from strands.tools import tool

from src.mcp._db import bronze_get, bronze_set

_FHFA_BASE_URL = "https://www.fhfa.gov/hpi/download/api"


@runtime_checkable
class _HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str]) -> Any: ...


def _fetch_price_index(
    metro_code: str,
    client: _HttpClient | None = None,
) -> dict[str, object]:
    """Check Bronze → call FHFA API → write Bronze → return HPI data.

    Raises:
        ValueError: If FHFA_API_KEY is not set.
        RuntimeError: If the FHFA API returns a non-2xx status.
    """
    cache_key = f"price_index:{metro_code}"
    cached = bronze_get("fhfa", cache_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("FHFA_API_KEY", "")
    if not api_key:
        return {}

    url = f"{_FHFA_BASE_URL}/hpi"
    params = {"metro_area": metro_code, "api_key": api_key, "format": "json"}

    try:
        if client is None:
            with httpx.Client(timeout=30.0) as _client:
                response = _client.get(url, params=params)
        else:
            response = client.get(url, params=params)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"FHFA API request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"FHFA API returned HTTP {response.status_code}: {response.text}")

    data: dict[str, object] = response.json()
    bronze_set("fhfa", cache_key, data)
    return data


@tool
def get_price_index(metro_code: str) -> dict[str, object]:
    """Fetch the FHFA House Price Index (HPI) for the given metro area code.

    Use CBSA codes such as C3562 for NYC-Newark-Jersey City. Returns quarterly
    HPI values showing price appreciation or depreciation trends. Rapid price
    decline over 2+ quarters is a leading distress indicator for commercial RE.
    Results are cached in Bronze — the API is not called twice for the same metro.
    """
    return _fetch_price_index(metro_code)
