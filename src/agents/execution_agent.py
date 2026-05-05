"""Execution agent — classifies Gold records and dispatches delivery.

Reads the ranked digest from the coordinator, applies Model / Monitor / Ignore
thresholds, generates briefs for MODEL ZIPs, and dispatches email + Slack.
"""

from __future__ import annotations

import dataclasses

from src.llm import LLMAdapter, get_adapter
from src.pipeline.action import ActionClassification, classify_action
from src.pipeline.briefs import OpportunityBrief, generate_brief
from src.pipeline.delivery import send_email_digest, send_slack_alert
from src.pipeline.normalizer import SilverRecord
from src.pipeline.scorer import GoldRecord


@dataclasses.dataclass(frozen=True)
class ExecutionResult:
    model_zips: tuple[str, ...]
    monitor_zips: tuple[str, ...]
    ignore_zips: tuple[str, ...]
    briefs: tuple[OpportunityBrief, ...]
    delivery_log: tuple[str, ...]


def execute(
    digest: tuple[GoldRecord, ...],
    silver_map: dict[str, SilverRecord],
    adapter: LLMAdapter | None = None,
) -> ExecutionResult:
    """Classify each Gold record, generate briefs for MODEL ZIPs, and deliver.

    Args:
        digest: Ranked GoldRecords from the coordinator.
        silver_map: ZIP → SilverRecord, needed to generate briefs.
        adapter: LLMAdapter for brief generation; defaults to get_adapter().
    """
    llm = adapter if adapter is not None else get_adapter()

    model_zips: list[str] = []
    monitor_zips: list[str] = []
    ignore_zips: list[str] = []
    briefs: list[OpportunityBrief] = []
    delivery_log: list[str] = []

    model_records: list[GoldRecord] = []

    for gold in digest:
        action = classify_action(gold.overall_score)

        if action == ActionClassification.MODEL:
            model_zips.append(gold.zip_code)
            model_records.append(gold)
            silver = silver_map.get(gold.zip_code)
            if silver is not None:
                brief = generate_brief(silver, gold, llm)
                briefs.append(brief)
            delivery_log.append(send_slack_alert(gold, action))

        elif action == ActionClassification.MONITOR:
            monitor_zips.append(gold.zip_code)
            delivery_log.append(send_slack_alert(gold, action))

        else:
            ignore_zips.append(gold.zip_code)

    if model_records:
        top_brief = briefs[0] if briefs else None
        delivery_log.append(
            send_email_digest(tuple(model_records), top_brief)
        )

    return ExecutionResult(
        model_zips=tuple(model_zips),
        monitor_zips=tuple(monitor_zips),
        ignore_zips=tuple(ignore_zips),
        briefs=tuple(briefs),
        delivery_log=tuple(delivery_log),
    )
