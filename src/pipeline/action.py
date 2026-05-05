"""Action classification — maps a Gold overall_score to Model / Monitor / Ignore."""

from __future__ import annotations

from enum import Enum

_MODEL_THRESHOLD = 70
_MONITOR_THRESHOLD = 40


class ActionClassification(Enum):
    MODEL = "model"      # score >= 70: high distress, generate brief + deliver
    MONITOR = "monitor"  # score 40–69: watch, low-priority alert
    IGNORE = "ignore"    # score < 40: below threshold, log only


def classify_action(overall_score: int) -> ActionClassification:
    """Return the action classification for a given overall distress score."""
    if overall_score >= _MODEL_THRESHOLD:
        return ActionClassification.MODEL
    if overall_score >= _MONITOR_THRESHOLD:
        return ActionClassification.MONITOR
    return ActionClassification.IGNORE
