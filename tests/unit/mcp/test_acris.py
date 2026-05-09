"""Tests for NYC ACRIS MCP — _fetch_acris_deeds."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, call, patch


def _mock_client(master_body: list, party_body: list | None = None) -> MagicMock:
    master_resp = MagicMock()
    master_resp.status_code = 200
    master_resp.json.return_value = master_body

    party_resp = MagicMock()
    party_resp.status_code = 200
    party_resp.json.return_value = party_body or []

    client = MagicMock()
    client.get.side_effect = [master_resp] + [party_resp] * len(master_body)
    return client


def _deed_record(doc_id: str = "DOC001") -> dict:
    return {"document_id": doc_id, "doc_type": "DEED", "recorded_datetime": "2026-04-01T00:00:00", "doc_amount": "500000"}


def _party_record(name: str = "SMITH, JOHN", addr: str = "123 MAIN ST") -> dict:
    return {
        "document_id": "DOC001",
        "party_type": "2",
        "name": name,
        "address_1": addr,
        "city": "NEW YORK",
        "state": "NY",
        "zip": "10001",
    }


class TestFetchAcrisDeedsCacheHit:
    def test_returns_cached_without_api_call(self) -> None:
        cached = {"records": [{"document_id": "DOC001", "buyer_name": "SMITH, JOHN"}]}
        with patch("src.mcp.acris.bronze_get", return_value=cached):
            with patch("src.mcp.acris.bronze_set") as mock_set:
                from src.mcp.acris import _fetch_acris_deeds

                client = MagicMock()
                result = _fetch_acris_deeds("10001", client=client)
                assert result == cached
                mock_set.assert_not_called()
                client.get.assert_not_called()

    def test_cache_key_uses_zip(self) -> None:
        with patch("src.mcp.acris.bronze_get") as mock_get:
            mock_get.return_value = None
            with patch("src.mcp.acris.bronze_set"):
                from src.mcp.acris import _fetch_acris_deeds

                client = _mock_client([_deed_record()])
                _fetch_acris_deeds("10014", client=client)
                mock_get.assert_called_with("acris", "deeds:10014")


class TestFetchAcrisDeedsCacheMiss:
    def test_writes_enriched_records_to_bronze(self) -> None:
        with patch("src.mcp.acris.bronze_get", return_value=None):
            with patch("src.mcp.acris.bronze_set") as mock_set:
                from src.mcp.acris import _fetch_acris_deeds

                client = _mock_client([_deed_record()], [_party_record()])
                _fetch_acris_deeds("10001", client=client)
                mock_set.assert_called_once()
                source, key, data = mock_set.call_args[0]
                assert source == "acris"
                assert key == "deeds:10001"
                assert len(data["records"]) == 1

    def test_enriches_record_with_buyer_info(self) -> None:
        with patch("src.mcp.acris.bronze_get", return_value=None):
            with patch("src.mcp.acris.bronze_set"):
                from src.mcp.acris import _fetch_acris_deeds

                client = _mock_client([_deed_record("DOC999")], [_party_record("JONES, BOB", "456 ELM ST")])
                result = _fetch_acris_deeds("10001", client=client)
                rec = result["records"][0]  # type: ignore[index]
                assert rec["buyer_name"] == "JONES, BOB"
                assert rec["buyer_address_1"] == "456 ELM ST"

    def test_missing_party_leaves_buyer_fields_none(self) -> None:
        with patch("src.mcp.acris.bronze_get", return_value=None):
            with patch("src.mcp.acris.bronze_set"):
                from src.mcp.acris import _fetch_acris_deeds

                client = _mock_client([_deed_record()], [])
                result = _fetch_acris_deeds("10001", client=client)
                rec = result["records"][0]  # type: ignore[index]
                assert rec["buyer_name"] is None
                assert rec["buyer_address_1"] is None

    def test_http_error_on_master_raises(self) -> None:
        import httpx
        from src.mcp.acris import _fetch_acris_deeds

        with patch("src.mcp.acris.bronze_get", return_value=None):
            client = MagicMock()
            client.get.side_effect = httpx.ConnectError("refused")
            import pytest
            with pytest.raises(RuntimeError, match="ACRIS master API request failed"):
                _fetch_acris_deeds("10001", client=client)


class TestGetAcrisDeedsTool:
    def test_delegates_to_fetch(self) -> None:
        expected = {"records": []}
        with patch("src.mcp.acris._fetch_acris_deeds", return_value=expected) as mock_fetch:
            from src.mcp.acris import get_acris_deeds

            result = get_acris_deeds("10001")
            assert result == expected
            mock_fetch.assert_called_once_with("10001")
