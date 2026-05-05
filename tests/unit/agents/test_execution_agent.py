"""Unit tests for src/agents/execution_agent.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.agents.execution_agent import ExecutionResult, execute
from src.pipeline.action import ActionClassification
from src.pipeline.briefs import OpportunityBrief
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


def _make_gold(zip_code: str, overall_score: int) -> GoldRecord:
    return GoldRecord(
        zip_code=zip_code,
        delinquency_score=60,
        employment_score=55,
        rent_vacancy_score=50,
        overall_score=overall_score,
        rationale="Test rationale.",
        rank=1,
    )


def _make_brief(zip_code: str) -> OpportunityBrief:
    return OpportunityBrief(
        zip_code=zip_code,
        rank=1,
        overall_score=75,
        headline="Test headline",
        summary="Test summary.",
        evidence_points=("ev1", "ev2", "ev3"),
        watch_items=("w1", "w2"),
    )


def test_execute_classifies_model_zip() -> None:
    gold = _make_gold("10001", overall_score=75)
    silver = _make_silver("10001")
    mock_brief = _make_brief("10001")
    adapter = MagicMock()

    with (
        patch("src.agents.execution_agent.generate_brief", return_value=mock_brief),
        patch("src.agents.execution_agent.send_slack_alert", return_value="slack:ok"),
        patch("src.agents.execution_agent.send_email_digest", return_value="email:ok"),
    ):
        result = execute(digest=(gold,), silver_map={"10001": silver}, adapter=adapter)

    assert "10001" in result.model_zips
    assert len(result.briefs) == 1
    assert "email:ok" in result.delivery_log


def test_execute_classifies_monitor_zip() -> None:
    gold = _make_gold("33101", overall_score=50)
    silver = _make_silver("33101")
    adapter = MagicMock()

    with (
        patch("src.agents.execution_agent.send_slack_alert", return_value="slack:monitor"),
        patch("src.agents.execution_agent.send_email_digest", return_value="email:ok"),
    ):
        result = execute(digest=(gold,), silver_map={"33101": silver}, adapter=adapter)

    assert "33101" in result.monitor_zips
    assert "33101" not in result.model_zips
    assert len(result.briefs) == 0


def test_execute_classifies_ignore_zip() -> None:
    gold = _make_gold("60601", overall_score=20)
    silver = _make_silver("60601")
    adapter = MagicMock()

    with patch("src.agents.execution_agent.send_email_digest"):
        result = execute(digest=(gold,), silver_map={"60601": silver}, adapter=adapter)

    assert "60601" in result.ignore_zips
    assert len(result.briefs) == 0
    assert "email" not in " ".join(result.delivery_log)


def test_execute_returns_execution_result_type() -> None:
    adapter = MagicMock()
    result = execute(digest=(), silver_map={}, adapter=adapter)
    assert isinstance(result, ExecutionResult)
    assert result.model_zips == ()
    assert result.monitor_zips == ()
    assert result.ignore_zips == ()


def test_execute_mixed_classifications() -> None:
    golds = (
        _make_gold("10001", overall_score=80),  # MODEL
        _make_gold("33101", overall_score=55),  # MONITOR
        _make_gold("60601", overall_score=15),  # IGNORE
    )
    silver_map = {
        "10001": _make_silver("10001"),
        "33101": _make_silver("33101"),
        "60601": _make_silver("60601"),
    }
    mock_brief = _make_brief("10001")
    adapter = MagicMock()

    with (
        patch("src.agents.execution_agent.generate_brief", return_value=mock_brief),
        patch("src.agents.execution_agent.send_slack_alert", return_value="slack:ok"),
        patch("src.agents.execution_agent.send_email_digest", return_value="email:ok"),
    ):
        result = execute(digest=golds, silver_map=silver_map, adapter=adapter)

    assert result.model_zips == ("10001",)
    assert result.monitor_zips == ("33101",)
    assert result.ignore_zips == ("60601",)
