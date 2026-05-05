"""Unit tests for src/pipeline/action.py."""

from __future__ import annotations

import dataclasses

import pytest
from src.pipeline.action import (
    MODEL_THRESHOLD,
    MONITOR_THRESHOLD,
    ActionLabel,
    classify,
)
from src.pipeline.scorer import GoldRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gold(score: int, zip_code: str = "10001") -> GoldRecord:
    return GoldRecord(
        zip_code=zip_code,
        delinquency_score=score,
        employment_score=score,
        rent_vacancy_score=score,
        overall_score=score,
        rationale="test rationale",
        rank=1,
    )


# ---------------------------------------------------------------------------
# ActionLabel enum values
# ---------------------------------------------------------------------------


def test_action_label_model_value() -> None:
    assert ActionLabel.MODEL.value == "model"


def test_action_label_monitor_value() -> None:
    assert ActionLabel.MONITOR.value == "monitor"


def test_action_label_ignore_value() -> None:
    assert ActionLabel.IGNORE.value == "ignore"


# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------


def test_model_threshold_value() -> None:
    assert MODEL_THRESHOLD == 70


def test_monitor_threshold_value() -> None:
    assert MONITOR_THRESHOLD == 40


# ---------------------------------------------------------------------------
# classify — MODEL tier (score >= 70)
# ---------------------------------------------------------------------------


def test_classify_score_70_is_model() -> None:
    result = classify(_gold(70))
    assert result.label == ActionLabel.MODEL


def test_classify_score_100_is_model() -> None:
    result = classify(_gold(100))
    assert result.label == ActionLabel.MODEL


# ---------------------------------------------------------------------------
# classify — MONITOR tier (40 <= score < 70)
# ---------------------------------------------------------------------------


def test_classify_score_69_is_monitor() -> None:
    result = classify(_gold(69))
    assert result.label == ActionLabel.MONITOR


def test_classify_score_40_is_monitor() -> None:
    result = classify(_gold(40))
    assert result.label == ActionLabel.MONITOR


# ---------------------------------------------------------------------------
# classify — IGNORE tier (score < 40)
# ---------------------------------------------------------------------------


def test_classify_score_39_is_ignore() -> None:
    result = classify(_gold(39))
    assert result.label == ActionLabel.IGNORE


def test_classify_score_0_is_ignore() -> None:
    result = classify(_gold(0))
    assert result.label == ActionLabel.IGNORE


# ---------------------------------------------------------------------------
# ActionResult field propagation
# ---------------------------------------------------------------------------


def test_classify_propagates_zip_code() -> None:
    result = classify(_gold(75, zip_code="90210"))
    assert result.zip_code == "90210"


def test_classify_propagates_score() -> None:
    result = classify(_gold(55))
    assert result.score == 55


def test_action_result_is_frozen() -> None:
    result = classify(_gold(80))
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        result.score = 0  # type: ignore[misc]
