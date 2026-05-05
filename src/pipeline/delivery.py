"""Delivery layer — SendGrid email and Slack alert dispatch.

Both functions are stub-safe: if the required env var is absent they return a
skip receipt instead of raising. Beatrice wires in the real implementations
once SENDGRID_API_KEY and SLACK_BOT_TOKEN arrive.
"""

from __future__ import annotations

import os

from src.pipeline.action import ActionClassification
from src.pipeline.briefs import OpportunityBrief
from src.pipeline.scorer import GoldRecord

_SLACK_CHANNEL = "#cre-signals"


def send_email_digest(
    records: tuple[GoldRecord, ...],
    brief: OpportunityBrief | None,
) -> str:
    """Send the daily digest email via SendGrid.

    Returns a receipt string (message ID or skip note).
    """
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    if not api_key:
        return "email:skipped:no_sendgrid_key"

    # TODO(beatrice): implement SendGrid template and send
    return f"email:stub:{len(records)}_records"


def send_slack_alert(
    record: GoldRecord,
    action: ActionClassification,
) -> str:
    """Post a distress alert to Slack.

    Returns a receipt string (message ts or skip note).
    """
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return f"slack:skipped:no_token:{record.zip_code}"

    # TODO(beatrice): implement Slack WebClient post_message
    label = action.value.upper()
    return f"slack:stub:{record.zip_code}:{label}:score={record.overall_score}"
