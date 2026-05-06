"""Execution agent — classify Gold records and dispatch delivery actions.

Classification thresholds:
    MODEL   >= 70  — generate opportunity brief, log email + Slack delivery
    MONITOR 40–69  — add to watchlist
    IGNORE  < 40   — log only

Delivery stubs:
    Email and Slack delivery are not yet implemented (src/pipeline/delivery.py
    is a future task).  This module logs what *would* be sent so the pipeline
    contract is testable without live credentials.
"""

from __future__ import annotations

import dataclasses
import logging
from enum import StrEnum

from src.pipeline._db import gold_get_digest
from src.pipeline.scorer import GoldRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Classification thresholds
# ---------------------------------------------------------------------------

_THRESHOLD_MODEL = 70
_THRESHOLD_MONITOR = 40


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class ActionClass(StrEnum):
    MODEL = "MODEL"
    MONITOR = "MONITOR"
    IGNORE = "IGNORE"


@dataclasses.dataclass(frozen=True)
class ClassifiedRecord:
    record: GoldRecord
    action: ActionClass


@dataclasses.dataclass(frozen=True)
class ExecutionResult:
    model_count: int
    monitor_count: int
    ignore_count: int
    classified: tuple[ClassifiedRecord, ...]


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------


def classify(overall_score: int) -> ActionClass:
    """Map an overall score to an ActionClass using the project thresholds.

    Args:
        overall_score: Integer 0–100 from GoldRecord.

    Returns:
        ActionClass.MODEL if >= 70, MONITOR if 40–69, IGNORE if < 40.
    """
    if overall_score >= _THRESHOLD_MODEL:
        return ActionClass.MODEL
    if overall_score >= _THRESHOLD_MONITOR:
        return ActionClass.MONITOR
    return ActionClass.IGNORE


# ---------------------------------------------------------------------------
# Execution agent
# ---------------------------------------------------------------------------


class ExecutionAgent:
    """Read the Gold digest, classify each record, and dispatch delivery stubs."""

    def run(self) -> ExecutionResult:
        """Execute the delivery pass over all current Gold records.

        Returns:
            ExecutionResult with counts and the full classified record list.
        """
        rows = gold_get_digest()
        classified_records: list[ClassifiedRecord] = []

        for row in rows:
            record = GoldRecord(
                zip_code=str(row["zip_code"]),
                delinquency_score=int(row["delinquency_score"]),
                employment_score=int(row["employment_score"]),
                rent_vacancy_score=int(row["rent_vacancy_score"]),
                overall_score=int(row["overall_score"]),
                rationale=str(row["rationale"]),
                rank=int(row["rank"]),
            )
            action = classify(record.overall_score)
            classified_records.append(ClassifiedRecord(record=record, action=action))

        model_recs = [c for c in classified_records if c.action == ActionClass.MODEL]
        monitor_recs = [c for c in classified_records if c.action == ActionClass.MONITOR]
        ignore_recs = [c for c in classified_records if c.action == ActionClass.IGNORE]

        self._dispatch_model(model_recs)
        self._dispatch_monitor(monitor_recs)
        self._dispatch_ignore(ignore_recs)

        return ExecutionResult(
            model_count=len(model_recs),
            monitor_count=len(monitor_recs),
            ignore_count=len(ignore_recs),
            classified=tuple(classified_records),
        )

    # ------------------------------------------------------------------
    # Delivery stubs — real delivery (SendGrid / Slack) is wired in later
    # ------------------------------------------------------------------

    def _dispatch_model(self, records: list[ClassifiedRecord]) -> None:
        for classified in records:
            r = classified.record
            # Stub: generate_brief() call will be wired when delivery.py exists.
            logger.info(
                "ACTION=MODEL zip=%s rank=%d score=%d | would send email + Slack",
                r.zip_code,
                r.rank,
                r.overall_score,
            )

    def _dispatch_monitor(self, records: list[ClassifiedRecord]) -> None:
        for classified in records:
            r = classified.record
            logger.info(
                "ACTION=MONITOR zip=%s rank=%d score=%d | added to watchlist",
                r.zip_code,
                r.rank,
                r.overall_score,
            )

    def _dispatch_ignore(self, records: list[ClassifiedRecord]) -> None:
        for classified in records:
            r = classified.record
            logger.debug(
                "ACTION=IGNORE zip=%s rank=%d score=%d",
                r.zip_code,
                r.rank,
                r.overall_score,
            )
