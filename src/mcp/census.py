"""Census ACS MCP server — get_demographics tool."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

import httpx
from strands.tools import tool

from src.mcp._db import bronze_get, bronze_set

_CENSUS_BASE_URL = "https://api.census.gov/data/2022/acs/acs5"

_ACS_VARIABLES = ",".join(
    [
        "B19013_001E",  # median household income
        "B25002_002E",  # occupied housing units
        "B25002_003E",  # vacant housing units
        "B23025_005E",  # unemployed civilians
        "B23025_002E",  # civilian labor force
    ]
)


@runtime_checkable
class _HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str]) -> Any: ...


def _fetch_demographics(
    census_tract: str,
    client: _HttpClient | None = None,
) -> dict[str, object]:
    """Check Bronze → call Census ACS API → write Bronze → return demographics.

    Raises:
        ValueError: If CENSUS_API_KEY is not set.
        RuntimeError: If the Census API returns a non-2xx status.
    """
    cache_key = f"demographics:{census_tract}"
    cached = bronze_get("census", cache_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("CENSUS_API_KEY", "")
    if not api_key:
        raise ValueError(
            "CENSUS_API_KEY environment variable is required. "
            "Get a free key at https://api.census.gov/data/key_signup.html"
        )

    state_fips = census_tract[:2]
    county_fips = census_tract[2:5]
    tract_code = census_tract[5:]

    params = {
        "get": _ACS_VARIABLES,
        "for": f"tract:{tract_code}",
        "in": f"state:{state_fips} county:{county_fips}",
        "key": api_key,
    }

    try:
        if client is None:
            with httpx.Client(timeout=30.0) as _client:
                response = _client.get(_CENSUS_BASE_URL, params=params)
        else:
            response = client.get(_CENSUS_BASE_URL, params=params)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Census API request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"Census API returned HTTP {response.status_code}: {response.text}")

    raw: list[list[str]] = response.json()
    headers = raw[0]
    values = raw[1] if len(raw) > 1 else []
    data: dict[str, object] = dict(zip(headers, values, strict=False))
    bronze_set("census", cache_key, data)
    return data


@tool
def get_demographics(census_tract: str) -> dict[str, object]:
    """Fetch ACS 5-year demographic estimates for the given Census tract.

    Pass the full 11-digit FIPS census tract code (e.g. '36061009900' for Manhattan).
    Returns median household income, housing vacancy rate, and unemployment rate —
    key socioeconomic context for CRE distress scoring.
    Results are cached in Bronze — the API is not called twice for the same tract.
    """
    return _fetch_demographics(census_tract)
