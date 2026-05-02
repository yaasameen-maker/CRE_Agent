"""Tests for Phase A demo helpers."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

from src.pipeline.briefs import OpportunityBrief
from src.pipeline.normalizer import SilverRecord
from src.pipeline.scorer import GoldRecord


def _make_temp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def _silver(zip_code: str) -> SilverRecord:
    return SilverRecord(
        zip_code=zip_code,
        delinquency_rate=3.8,
        delinquency_date="2025-10-01",
        unemployment_rate=5.2,
        unemployment_mom_change=0.4,
        average_rent=3200.0,
        median_rent=3100.0,
        rent_change_pct=-2.1,
        vacancy_rate=7.0,
    )


class TestParseZipsArgument:
    def test_normalizes_whitespace_and_dedupes(self) -> None:
        from src.pipeline.demo import parse_zips_argument

        assert parse_zips_argument(" 10001, 60601,10001 ,33101 ") == ["10001", "60601", "33101"]

    def test_requires_at_least_one_zip(self) -> None:
        import pytest
        from src.pipeline.demo import parse_zips_argument

        with pytest.raises(ValueError, match="At least one ZIP code"):
            parse_zips_argument(" ,, ")


class TestResolveDemoZips:
    def test_unsupported_zip_raises_with_supported_list(self) -> None:
        import pytest
        from src.pipeline.demo import resolve_demo_zips

        with pytest.raises(ValueError, match="Supported demo ZIPs"):
            resolve_demo_zips(["99999"])


class TestRunDemoForZips:
    def test_partial_success_keeps_ranked_results_and_failure_reasons(self) -> None:
        from src.pipeline.demo import run_demo_for_zips

        path = _make_temp_db()
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                with patch("src.pipeline.demo.get_delinquency_rate"):
                    with patch("src.pipeline.demo.get_employment_trend"):
                        with patch("src.pipeline.demo.get_rent_trend"):
                            with patch("src.pipeline.demo.get_vacancy_rate"):
                                with patch(
                                    "src.pipeline.demo.normalize_zip",
                                    side_effect=[_silver("10001"), None],
                                ):
                                    with patch(
                                        "src.pipeline.demo.score_zip",
                                        return_value=GoldRecord(
                                            zip_code="10001",
                                            delinquency_score=70,
                                            employment_score=60,
                                            rent_vacancy_score=50,
                                            overall_score=63,
                                            rationale="Strong signal",
                                            rank=0,
                                        ),
                                    ):
                                        with patch(
                                            "src.pipeline.demo.generate_brief",
                                            return_value=OpportunityBrief(
                                                zip_code="10001",
                                                rank=1,
                                                overall_score=63,
                                                headline="Headline",
                                                summary="Summary",
                                                evidence_points=("A", "B", "C"),
                                                watch_items=("W1", "W2"),
                                            ),
                                        ):
                                            result = run_demo_for_zips(
                                                ["10001", "33101"], adapter=MagicMock()
                                            )

            assert len(result.digest) == 1
            assert result.digest[0].rank == 1
            assert result.brief is not None
            assert len(result.failures) == 1
            assert result.failures[0].zip_code == "33101"
        finally:
            os.unlink(path)
