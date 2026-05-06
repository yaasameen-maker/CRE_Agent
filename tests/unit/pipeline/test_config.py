"""Tests for NYC scope configuration."""

from __future__ import annotations

import os
from unittest.mock import patch


class TestNycZipCodes:
    def test_manhattan_zip_in_set(self) -> None:
        from src.pipeline.config import NYC_ZIP_CODES

        assert "10001" in NYC_ZIP_CODES
        assert "10282" in NYC_ZIP_CODES

    def test_bronx_zip_in_set(self) -> None:
        from src.pipeline.config import NYC_ZIP_CODES

        assert "10451" in NYC_ZIP_CODES
        assert "10475" in NYC_ZIP_CODES

    def test_brooklyn_zip_in_set(self) -> None:
        from src.pipeline.config import NYC_ZIP_CODES

        assert "11201" in NYC_ZIP_CODES
        assert "11256" in NYC_ZIP_CODES

    def test_queens_zip_in_set(self) -> None:
        from src.pipeline.config import NYC_ZIP_CODES

        assert "11101" in NYC_ZIP_CODES
        assert "11106" in NYC_ZIP_CODES

    def test_staten_island_zip_in_set(self) -> None:
        from src.pipeline.config import NYC_ZIP_CODES

        assert "10301" in NYC_ZIP_CODES
        assert "10314" in NYC_ZIP_CODES

    def test_non_nyc_zip_not_in_set(self) -> None:
        from src.pipeline.config import NYC_ZIP_CODES

        assert "90210" not in NYC_ZIP_CODES
        assert "33101" not in NYC_ZIP_CODES
        assert "60601" not in NYC_ZIP_CODES


class TestIsNycZip:
    def test_nyc_zip_returns_true(self) -> None:
        from src.pipeline.config import is_nyc_zip

        assert is_nyc_zip("10001") is True
        assert is_nyc_zip("11201") is True

    def test_non_nyc_zip_returns_false(self) -> None:
        from src.pipeline.config import is_nyc_zip

        assert is_nyc_zip("90210") is False
        assert is_nyc_zip("00000") is False


class TestFilterNycZips:
    def test_filters_non_nyc_when_scope_enabled(self) -> None:
        with patch.dict(os.environ, {"SCOPE_NYC_ONLY": "true"}):
            import importlib

            import src.pipeline.config as cfg

            importlib.reload(cfg)
            result = cfg.filter_nyc_zips(["10001", "90210", "11201", "33101"])
        assert result == ["10001", "11201"]

    def test_returns_all_when_scope_disabled(self) -> None:
        with patch.dict(os.environ, {"SCOPE_NYC_ONLY": "false"}):
            import importlib

            import src.pipeline.config as cfg

            importlib.reload(cfg)
            result = cfg.filter_nyc_zips(["10001", "90210", "11201", "33101"])
        assert result == ["10001", "90210", "11201", "33101"]

    def test_empty_list_returns_empty(self) -> None:
        from src.pipeline.config import filter_nyc_zips

        assert filter_nyc_zips([]) == []

    def test_all_nyc_zips_pass_filter(self) -> None:
        with patch.dict(os.environ, {"SCOPE_NYC_ONLY": "true"}):
            import importlib

            import src.pipeline.config as cfg

            importlib.reload(cfg)
            zips = ["10001", "10014", "10036", "11201"]
            assert cfg.filter_nyc_zips(zips) == zips
