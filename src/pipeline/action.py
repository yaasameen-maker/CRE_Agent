"""Action classifier — maps a GoldRecord score to a Model/Monitor/Ignore label."""

from __future__ import annotations

import dataclasses
from enum import Enum

from src.pipeline.scorer import GoldRecord

MODEL_THRESHOLD: int = 70
MONITOR_THRESHOLD: int = 40


class ActionLabel(Enum):
    MODEL = "model"  # overall_score >= 70
    MONITOR = "monitor"  # 40 <= overall_score < 70
    IGNORE = "ignore"  # overall_score < 40


@dataclasses.dataclass(frozen=True)
class ActionResult:
    zip_code: str
    label: ActionLabel
    score: int


def classify(record: GoldRecord) -> ActionResult:
    """Return an ActionResult with the correct label based on overall_score."""
    score = record.overall_score
    if score >= MODEL_THRESHOLD:
        label = ActionLabel.MODEL
    elif score >= MONITOR_THRESHOLD:
        label = ActionLabel.MONITOR
    else:
        label = ActionLabel.IGNORE
    return ActionResult(zip_code=record.zip_code, label=label, score=score)
