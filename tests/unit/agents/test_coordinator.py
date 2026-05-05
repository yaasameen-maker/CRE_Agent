"""Unit tests for src/agents/coordinator.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.coordinator import CoordinatorResult, run_coordinator
from src.pipeline.demo import DemoFailure
from src.pipeline.normalizer import SilverRecord
from src.pipeline.scorer import GoldRecord


def _make_silver(zip_code: str = "10001") -> SilverRecord:
    return SilverRecord(
        zip_code=zip_code,
        delinquency_rate=3.5,
        delinquency_date="2024-10-01",
        unemployment_rate=5.2,
        unemployment_mom_change=0.2,
        average_rent=2800.0,
        median_rent=2600.0,
        rent_change_pct=-1.5,
        vacancy_rate=7.0,
    )


def _make_gold(zip_code: str = "10001", overall_score: int = 65) -> GoldRecord:
    return GoldRecord(
        zip_code=zip_code,
        delinquency_score=60,
        employment_score=55,
        rent_vacancy_score=50,
        overall_score=overall_score,
        rationale="Test rationale.",
        rank=0,
    )


def test_run_coordinator_returns_coordinator_result() -> None:
    silver = _make_silver("10001")
    gold = _make_gold("10001")

    with (
        patch("src.agents.coordinator.get_delinquency_rate"),
        patch("src.agents.coordinator.get_employment_trend"),
        patch("src.agents.coordinator.get_rent_trend"),
        patch("src.agents.coordinator.get_vacancy_rate"),
        patch("src.agents.coordinator.normalize_zip", return_value=silver),
        patch("src.agents.coordinator.silver_upsert"),
        patch("src.agents.coordinator.score_zip", return_value=gold),
        patch("src.agents.coordinator.get_adapter", return_value=MagicMock()),
    ):
        result = run_coordinator(["10001"])

    assert isinstance(result, CoordinatorResult)
    assert len(result.digest) == 1
    assert result.digest[0].zip_code == "10001"
    assert result.digest[0].rank == 1
    assert "10001" in result.silver_map
    assert len(result.failures) == 0


def test_run_coordinator_parallel_multiple_zips() -> None:
    def make_silver(zip_code: str) -> SilverRecord:
        return _make_silver(zip_code)

    def make_gold(silver: SilverRecord, adapter: object) -> GoldRecord:
        return _make_gold(silver.zip_code)

    with (
        patch("src.agents.coordinator.get_delinquency_rate"),
        patch("src.agents.coordinator.get_employment_trend"),
        patch("src.agents.coordinator.get_rent_trend"),
        patch("src.agents.coordinator.get_vacancy_rate"),
        patch("src.agents.coordinator.normalize_zip", side_effect=make_silver),
        patch("src.agents.coordinator.silver_upsert"),
        patch("src.agents.coordinator.score_zip", side_effect=make_gold),
        patch("src.agents.coordinator.get_adapter", return_value=MagicMock()),
    ):
        result = run_coordinator(["10001", "33101", "60601"])

    assert len(result.digest) == 3
    assert len(result.silver_map) == 3
    assert len(result.failures) == 0


def test_run_coordinator_records_failure_on_exception() -> None:
    with (
        patch("src.agents.coordinator.get_delinquency_rate", side_effect=RuntimeError("API down")),
        patch("src.agents.coordinator.get_adapter", return_value=MagicMock()),
    ):
        result = run_coordinator(["10001"])

    assert len(result.failures) == 1
    assert result.failures[0].zip_code == "10001"
    assert "API down" in result.failures[0].reason


def test_run_coordinator_raises_for_unsupported_zip() -> None:
    with pytest.raises(ValueError, match="Unsupported ZIP codes"):
        run_coordinator(["99999"])


def test_run_coordinator_silver_none_records_failure() -> None:
    with (
        patch("src.agents.coordinator.get_delinquency_rate"),
        patch("src.agents.coordinator.get_employment_trend"),
        patch("src.agents.coordinator.get_rent_trend"),
        patch("src.agents.coordinator.get_vacancy_rate"),
        patch("src.agents.coordinator.normalize_zip", return_value=None),
        patch("src.agents.coordinator.get_adapter", return_value=MagicMock()),
    ):
        result = run_coordinator(["10001"])

    assert len(result.failures) == 1
    assert result.failures[0].zip_code == "10001"
