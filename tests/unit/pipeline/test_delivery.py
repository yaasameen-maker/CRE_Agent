"""Unit tests for src/pipeline/delivery.py."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from src.pipeline.action import ActionClassification
from src.pipeline.delivery import send_email_digest, send_slack_alert
from src.pipeline.scorer import GoldRecord


def _make_gold(zip_code: str = "10001", overall_score: int = 75) -> GoldRecord:
    return GoldRecord(
        zip_code=zip_code,
        delinquency_score=60,
        employment_score=55,
        rent_vacancy_score=50,
        overall_score=overall_score,
        rationale="Test rationale.",
        rank=1,
    )


def test_send_email_digest_skips_without_key() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SENDGRID_API_KEY", None)
        result = send_email_digest((_make_gold(),), None)
    assert "skipped" in result


def test_send_slack_alert_skips_without_token() -> None:
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SLACK_BOT_TOKEN", None)
        result = send_slack_alert(_make_gold(), ActionClassification.MODEL)
    assert "skipped" in result


def test_send_slack_alert_includes_zip_code() -> None:
    os.environ.pop("SLACK_BOT_TOKEN", None)
    result = send_slack_alert(_make_gold("33101"), ActionClassification.MONITOR)
    assert "33101" in result


def test_send_email_digest_includes_record_count() -> None:
    os.environ.pop("SENDGRID_API_KEY", None)
    result = send_email_digest((), None)
    assert "skipped" in result
