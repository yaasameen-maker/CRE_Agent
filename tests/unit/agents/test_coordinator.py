"""Tests for src/agents/coordinator.py."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from src.pipeline.scorer import GoldRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ZIP_CONFIGS = [
    {"zip_code": "10001", "metro_code": "METRO_A", "fred_series_id": "FRED_A"},
    {"zip_code": "10014", "metro_code": "METRO_B", "fred_series_id": "FRED_B"},
    {"zip_code": "11201", "metro_code": "METRO_C", "fred_series_id": "FRED_C"},
]


def _gold(zip_code: str, score: int) -> GoldRecord:
    return GoldRecord(
        zip_code=zip_code,
        delinquency_score=score,
        employment_score=score,
        rent_vacancy_score=score,
        overall_score=score,
        rationale="test rationale",
        rank=0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunCoordinatorEmpty:
    def test_empty_input_returns_empty_list(self) -> None:
        from src.agents.coordinator import run_coordinator

        result = asyncio.run(run_coordinator([]))
        assert result == []


class TestRunCoordinatorSuccess:
    def test_returns_sorted_gold_records(self) -> None:
        """Coordinator sorts by overall_score descending and assigns ranks."""
        from src.agents.coordinator import run_coordinator

        def fake_score(cfg: dict) -> GoldRecord:
            scores = {"10001": 45, "10014": 75, "11201": 30}
            return _gold(cfg["zip_code"], scores[cfg["zip_code"]])

        with (
            patch(
                "src.agents.coordinator.score_zip_for_coordinator",
                side_effect=fake_score,
            ),
            patch("src.agents.coordinator.gold_upsert") as mock_upsert,
        ):
            result = asyncio.run(run_coordinator(_ZIP_CONFIGS))

        # Three records returned.
        assert len(result) == 3

        # Ranked descending by overall_score.
        assert result[0].zip_code == "10014"
        assert result[0].rank == 1
        assert result[1].zip_code == "10001"
        assert result[1].rank == 2
        assert result[2].zip_code == "11201"
        assert result[2].rank == 3

        # gold_upsert called once per record.
        assert mock_upsert.call_count == 3

    def test_gold_upsert_receives_correct_args(self) -> None:
        """Each GoldRecord is persisted with correct fields."""
        from src.agents.coordinator import run_coordinator

        def fake_score(cfg: dict) -> GoldRecord:
            return _gold(cfg["zip_code"], 55)

        with (
            patch("src.agents.coordinator.score_zip_for_coordinator", side_effect=fake_score),
            patch("src.agents.coordinator.gold_upsert") as mock_upsert,
        ):
            asyncio.run(run_coordinator([_ZIP_CONFIGS[0]]))

        call_kwargs = mock_upsert.call_args[1]
        assert call_kwargs["zip_code"] == "10001"
        assert call_kwargs["overall_score"] == 55
        assert call_kwargs["rank"] == 1


class TestRunCoordinatorFaultIsolation:
    def test_none_result_excluded_from_digest(self) -> None:
        """A ZIP that scores None is silently excluded; others still rank."""
        from src.agents.coordinator import run_coordinator

        def fake_score(cfg: dict) -> GoldRecord | None:
            if cfg["zip_code"] == "10014":
                return None  # data unavailable
            return _gold(cfg["zip_code"], 50)

        with (
            patch("src.agents.coordinator.score_zip_for_coordinator", side_effect=fake_score),
            patch("src.agents.coordinator.gold_upsert"),
        ):
            result = asyncio.run(run_coordinator(_ZIP_CONFIGS))

        # Only the two non-None records are returned.
        zip_codes = {r.zip_code for r in result}
        assert "10014" not in zip_codes
        assert len(result) == 2

    def test_exception_in_one_zip_does_not_crash_run(self) -> None:
        """An unhandled exception from one ZIP is logged; others complete."""
        from src.agents.coordinator import run_coordinator

        def fake_score(cfg: dict) -> GoldRecord:
            if cfg["zip_code"] == "11201":
                raise RuntimeError("network timeout")
            return _gold(cfg["zip_code"], 40)

        with (
            patch("src.agents.coordinator.score_zip_for_coordinator", side_effect=fake_score),
            patch("src.agents.coordinator.gold_upsert"),
        ):
            result = asyncio.run(run_coordinator(_ZIP_CONFIGS))

        zip_codes = {r.zip_code for r in result}
        assert "11201" not in zip_codes
        assert len(result) == 2

    def test_all_none_returns_empty(self) -> None:
        """When every ZIP returns None, coordinator returns an empty list."""
        from src.agents.coordinator import run_coordinator

        with (
            patch("src.agents.coordinator.score_zip_for_coordinator", return_value=None),
            patch("src.agents.coordinator.gold_upsert"),
        ):
            result = asyncio.run(run_coordinator(_ZIP_CONFIGS))

        assert result == []

    def test_single_zip_gets_rank_one(self) -> None:
        """A single successful record gets rank 1."""
        from src.agents.coordinator import run_coordinator

        with (
            patch(
                "src.agents.coordinator.score_zip_for_coordinator",
                return_value=_gold("10001", 65),
            ),
            patch("src.agents.coordinator.gold_upsert"),
        ):
            result = asyncio.run(run_coordinator([_ZIP_CONFIGS[0]]))

        assert len(result) == 1
        assert result[0].rank == 1
