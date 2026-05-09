"""NYC ACRIS MCP — deed transfer leads from NYC open data (no API key required).

Socrata dataset: Real Property Master (bnx9-e6tj)
Parties dataset: Real Property Parties (636b-3b5g)
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx
from strands.tools import tool

from src.mcp._db import bronze_get, bronze_set

_ACRIS_MASTER_URL = "https://data.cityofnewyork.us/resource/bnx9-e6tj.json"
_ACRIS_PARTIES_URL = "https://data.cityofnewyork.us/resource/636b-3b5g.json"


@runtime_checkable
class _HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str]) -> Any: ...


def _fetch_acris_deeds(
    zip_code: str,
    limit: int = 50,
    client: _HttpClient | None = None,
) -> dict[str, object]:
    """Check Bronze → call ACRIS API → write Bronze → return deed transfer records.

    Pulls recent DEED documents for the ZIP from the ACRIS Real Property Master
    table, then enriches each document with grantee (buyer) info from the
    Parties table.  No API key required — NYC open data via Socrata.

    Raises:
        RuntimeError: If either ACRIS endpoint returns a non-2xx status.
    """
    cache_key = f"deeds:{zip_code}"
    cached = bronze_get("acris", cache_key)
    if cached is not None:
        return cached

    master_params = {
        "$where": f"zip='{zip_code}' AND doc_type='DEED'",
        "$limit": str(limit),
        "$order": "recorded_datetime DESC",
    }

    try:
        if client is None:
            with httpx.Client(timeout=30.0) as _client:
                master_resp = _client.get(_ACRIS_MASTER_URL, params=master_params)
        else:
            master_resp = client.get(_ACRIS_MASTER_URL, params=master_params)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"ACRIS master API request failed: {exc}") from exc

    if master_resp.status_code < 200 or master_resp.status_code >= 300:
        raise RuntimeError(
            f"ACRIS master API returned HTTP {master_resp.status_code}: {master_resp.text}"
        )

    records: list[dict[str, object]] = master_resp.json()

    # Enrich each document with grantee (buyer) party info.
    enriched: list[dict[str, object]] = []
    for rec in records:
        doc_id = rec.get("document_id", "")
        party_params = {
            "$where": f"document_id='{doc_id}' AND party_type='2'",
            "$limit": "1",
        }
        try:
            if client is None:
                with httpx.Client(timeout=15.0) as _client:
                    party_resp = _client.get(_ACRIS_PARTIES_URL, params=party_params)
            else:
                party_resp = client.get(_ACRIS_PARTIES_URL, params=party_params)
            parties: list[dict[str, object]] = (
                party_resp.json() if party_resp.status_code == 200 else []
            )
        except httpx.HTTPError:
            parties = []

        buyer = parties[0] if parties else {}
        enriched.append({
            "document_id": doc_id,
            "recorded_datetime": rec.get("recorded_datetime"),
            "doc_amount": rec.get("doc_amount"),
            "buyer_name": buyer.get("name"),
            "buyer_address_1": buyer.get("address_1"),
            "buyer_address_2": buyer.get("address_2"),
            "buyer_city": buyer.get("city"),
            "buyer_state": buyer.get("state"),
            "buyer_zip": buyer.get("zip"),
        })

    data: dict[str, object] = {"records": enriched}
    bronze_set("acris", cache_key, data)
    return data


@tool
def get_acris_deeds(zip_code: str) -> dict[str, object]:
    """Fetch recent deed transfers from NYC ACRIS for the given ZIP code.

    Returns the 50 most-recent DEED documents with grantee (buyer) name
    and mailing address.  Data is sourced from the NYC open data portal —
    no API key required.  Results are Bronze-cached to avoid duplicate calls.
    """
    return _fetch_acris_deeds(zip_code)
