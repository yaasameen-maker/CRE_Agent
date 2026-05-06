"""NYC scope configuration for the CRE Signal Agent."""

from __future__ import annotations

import os

# ─── NYC ZIP codes by borough ─────────────────────────────────────────────────

_MANHATTAN = frozenset(str(z) for z in range(10001, 10283))
_BRONX = frozenset(str(z) for z in range(10451, 10476))
_BROOKLYN = frozenset(str(z) for z in range(11201, 11257))
_QUEENS = frozenset(str(z) for z in range(11101, 11107))
_STATEN_ISLAND = frozenset(str(z) for z in range(10301, 10315))

NYC_ZIP_CODES: frozenset[str] = _MANHATTAN | _BRONX | _BROOKLYN | _QUEENS | _STATEN_ISLAND

# ─── Metro and series identifiers ─────────────────────────────────────────────

NYC_METRO_CODE = "LAUMT364002000000003"  # NYC metro BLS LAUS unemployment series
NYC_FRED_SERIES = "DRCRELEXFNM"  # CRE delinquency — national proxy (best available)

# ─── Feature toggle ───────────────────────────────────────────────────────────

SCOPE_NYC_ONLY: bool = os.getenv("SCOPE_NYC_ONLY", "true").lower() == "true"


def is_nyc_zip(zip_code: str) -> bool:
    """Return True if the ZIP code is within the NYC five-borough scope."""
    return zip_code in NYC_ZIP_CODES


def filter_nyc_zips(zip_codes: list[str]) -> list[str]:
    """Return only the ZIPs that are within the NYC scope.

    If SCOPE_NYC_ONLY is False, returns the full input list unchanged.
    """
    if not SCOPE_NYC_ONLY:
        return zip_codes
    return [z for z in zip_codes if is_nyc_zip(z)]
