"""Unit tests for src/pipeline/action.py."""

from __future__ import annotations

import pytest

from src.pipeline.action import ActionClassification, classify_action


@pytest.mark.parametrize(
    "score, expected",
    [
        (100, ActionClassification.MODEL),
        (70, ActionClassification.MODEL),
        (69, ActionClassification.MONITOR),
        (50, ActionClassification.MONITOR),
        (40, ActionClassification.MONITOR),
        (39, ActionClassification.IGNORE),
        (20, ActionClassification.IGNORE),
        (0, ActionClassification.IGNORE),
    ],
)
def test_classify_action_thresholds(score: int, expected: ActionClassification) -> None:
    assert classify_action(score) == expected


def test_action_classification_values() -> None:
    assert ActionClassification.MODEL.value == "model"
    assert ActionClassification.MONITOR.value == "monitor"
    assert ActionClassification.IGNORE.value == "ignore"
