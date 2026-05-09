"""NYC DOB MCP — building violations from NYC open data (no API key required).

Socrata dataset: DOB Violations (3h2n-5cm9)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, runtime_checkable

import httpx
from strands.tools import tool

from src.mcp._db import bronze_get, bronze_set

_DOB_VIOLATIONS_URL = "https://data.cityofnewyork.us/resource/3h2n-5cm9.json"


@runtime_checkable
class _HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str]) -> Any: ...


def _fetch_dob_violations(
    zip_code: str,
    days_back: int = 90,
    limit: int = 200,
    client: _HttpClient | None = None,
) -> dict[str, object]:
    """Check Bronze → call DOB API → write Bronze → return violation records.

    Fetches building violations filed against properties in the ZIP code over
    the given lookback window.  A spike in violations signals structural
    neglect and potential distress.  No API key required.

    Raises:
        RuntimeError: If the DOB endpoint returns a non-2xx status.
    """
    cache_key = f"violations:{zip_code}:{days_back}"
    cached = bronze_get("dob", cache_key)
    if cached is not None:
        return cached

    since = (datetime.now(UTC) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
    params = {
        "$where": f"zip_code='{zip_code}' AND issue_date >= '{since}'",
        "$limit": str(limit),
        "$order": "issue_date DESC",
    }

    try:
        if client is None:
            with httpx.Client(timeout=30.0) as _client:
                response = _client.get(_DOB_VIOLATIONS_URL, params=params)
        else:
            response = client.get(_DOB_VIOLATIONS_URL, params=params)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"DOB API request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(
            f"DOB API returned HTTP {response.status_code}: {response.text}"
        )

    data: dict[str, object] = {"records": response.json(), "days_back": days_back}
    bronze_set("dob", cache_key, data)
    return data


@tool
def get_dob_violations(zip_code: str) -> dict[str, object]:
    """Fetch recent building violations from NYC DOB for the given ZIP code.

    Returns violations filed in the last 90 days.  High violation counts
    indicate structural neglect and owner distress — a leading indicator
    for CRE acquisition opportunities.  No API key required.
    Results are Bronze-cached to avoid duplicate calls.
    """
    return _fetch_dob_violations(zip_code)
