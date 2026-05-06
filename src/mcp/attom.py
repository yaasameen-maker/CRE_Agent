"""ATTOM MCP server — get_foreclosure_filings and get_deed_transfers tools."""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

import httpx
from strands.tools import tool

from src.mcp._db import bronze_get, bronze_set

_ATTOM_BASE_URL = "https://api.gateway.attomdata.com/propertyapi/v1.0.0"


@runtime_checkable
class _HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> Any: ...


def _fetch_foreclosure_filings(
    zip_code: str,
    days_back: int = 90,
    client: _HttpClient | None = None,
) -> dict[str, object]:
    """Check Bronze → call ATTOM API → write Bronze → return foreclosure filings.

    Raises:
        ValueError: If ATTOM_API_KEY is not set.
        RuntimeError: If the ATTOM API returns a non-2xx status.
    """
    cache_key = f"foreclosures:{zip_code}:{days_back}"
    cached = bronze_get("attom", cache_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("ATTOM_API_KEY", "")
    if not api_key:
        raise ValueError(
            "ATTOM_API_KEY environment variable is required. "
            "Get a key at https://api.attomdata.com/"
        )

    url = f"{_ATTOM_BASE_URL}/assessment/detail"
    params = {
        "postalcode": zip_code,
        "categoryName": "NOTICE OF DEFAULT",
        "daysback": str(days_back),
    }
    headers = {"apikey": api_key, "accept": "application/json"}

    try:
        if client is None:
            with httpx.Client(timeout=30.0) as _client:
                response = _client.get(url, params=params, headers=headers)
        else:
            response = client.get(url, params=params, headers=headers)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"ATTOM API request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"ATTOM API returned HTTP {response.status_code}: {response.text}")

    data: dict[str, object] = response.json()
    bronze_set("attom", cache_key, data)
    return data


def _fetch_deed_transfers(
    zip_code: str,
    days_back: int = 90,
    client: _HttpClient | None = None,
) -> dict[str, object]:
    """Check Bronze → call ATTOM API → write Bronze → return deed transfers.

    Raises:
        ValueError: If ATTOM_API_KEY is not set.
        RuntimeError: If the ATTOM API returns a non-2xx status.
    """
    cache_key = f"deeds:{zip_code}:{days_back}"
    cached = bronze_get("attom", cache_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("ATTOM_API_KEY", "")
    if not api_key:
        raise ValueError(
            "ATTOM_API_KEY environment variable is required. "
            "Get a key at https://api.attomdata.com/"
        )

    url = f"{_ATTOM_BASE_URL}/sale/detail"
    params = {"postalcode": zip_code, "daysback": str(days_back)}
    headers = {"apikey": api_key, "accept": "application/json"}

    try:
        if client is None:
            with httpx.Client(timeout=30.0) as _client:
                response = _client.get(url, params=params, headers=headers)
        else:
            response = client.get(url, params=params, headers=headers)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"ATTOM API request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"ATTOM API returned HTTP {response.status_code}: {response.text}")

    data: dict[str, object] = response.json()
    bronze_set("attom", cache_key, data)
    return data


@tool
def get_foreclosure_filings(zip_code: str, days_back: int = 90) -> dict[str, object]:
    """Fetch foreclosure filings from ATTOM for the given ZIP code.

    Returns notice-of-default and foreclosure filing records for properties
    in the ZIP code over the specified lookback window. High filing counts
    signal distress in the local commercial real estate market.
    Results are cached in Bronze — the API is not called twice for the same ZIP + window.
    """
    return _fetch_foreclosure_filings(zip_code, days_back)


@tool
def get_deed_transfers(zip_code: str, days_back: int = 90) -> dict[str, object]:
    """Fetch deed transfer (sale) records from ATTOM for the given ZIP code.

    Returns recent property sale transactions in the ZIP code. Abnormal transfer
    velocity — either very high (distressed liquidations) or very low (frozen market)
    — is a distress indicator.
    Results are cached in Bronze — the API is not called twice for the same ZIP + window.
    """
    return _fetch_deed_transfers(zip_code, days_back)
