"""HUD MCP server — get_hud_vacancy tool."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

import httpx
from strands.tools import tool

from src.mcp._db import bronze_get, bronze_set

_HUD_BASE_URL = "https://www.huduser.gov/hudapi/public/usps"


@runtime_checkable
class _HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> Any: ...


def _fetch_hud_vacancy(
    metro_code: str,
    client: _HttpClient | None = None,
) -> dict[str, object]:
    """Check Bronze → call HUD API → write Bronze → return vacancy data.

    Raises:
        ValueError: If HUD_API_KEY is not set.
        RuntimeError: If the HUD API returns a non-2xx status.
    """
    cache_key = f"hud_vacancy:{metro_code}"
    cached = bronze_get("hud", cache_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("HUD_API_KEY", "")
    if not api_key:
        raise ValueError(
            "HUD_API_KEY environment variable is required. "
            "Register at https://www.huduser.gov/portal/dataset/uspszip-api.html"
        )

    params = {"type": "3", "query": metro_code}
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        if client is None:
            with httpx.Client(timeout=30.0) as _client:
                response = _client.get(_HUD_BASE_URL, params=params, headers=headers)
        else:
            response = client.get(_HUD_BASE_URL, params=params, headers=headers)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"HUD API request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"HUD API returned HTTP {response.status_code}: {response.text}")

    data: dict[str, object] = response.json()
    bronze_set("hud", cache_key, data)
    return data


@tool
def get_hud_vacancy(metro_code: str) -> dict[str, object]:
    """Fetch HUD USPS vacancy data for the given metro area code.

    Pass a CBSA or HUD metro code (e.g. 'METRO35620M35620' for NYC). Returns
    quarterly address vacancy rates by ZIP code within the metro. Elevated vacancy
    rates — especially in commercial/mixed-use ZIP codes — are a strong distress
    signal. Results are cached in Bronze — the API is not called twice for the same metro.
    """
    return _fetch_hud_vacancy(metro_code)
