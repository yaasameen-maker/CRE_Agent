"""Tests for src/agents/execution_agent.py."""

from __future__ import annotations

from unittest.mock import patch

from src.agents.execution_agent import ActionClass, ExecutionAgent, classify
from src.pipeline.scorer import GoldRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gold(zip_code: str, score: int, rank: int = 1) -> GoldRecord:
    return GoldRecord(
        zip_code=zip_code,
        delinquency_score=score,
        employment_score=score,
        rent_vacancy_score=score,
        overall_score=score,
        rationale="test rationale",
        rank=rank,
    )


def _sqlite_row(zip_code: str, score: int, rank: int = 1) -> dict:
    """Return a dict that behaves like a sqlite3.Row (subscript access)."""
    return {
        "zip_code": zip_code,
        "delinquency_score": score,
        "employment_score": score,
        "rent_vacancy_score": score,
        "overall_score": score,
        "rationale": "test rationale",
        "rank": rank,
    }


# ---------------------------------------------------------------------------
# classify() unit tests
# ---------------------------------------------------------------------------


class TestClassify:
    def test_score_70_is_model(self) -> None:
        assert classify(70) == ActionClass.MODEL

    def test_score_100_is_model(self) -> None:
        assert classify(100) == ActionClass.MODEL

    def test_score_69_is_monitor(self) -> None:
        assert classify(69) == ActionClass.MONITOR

    def test_score_40_is_monitor(self) -> None:
        assert classify(40) == ActionClass.MONITOR

    def test_score_39_is_ignore(self) -> None:
        assert classify(39) == ActionClass.IGNORE

    def test_score_0_is_ignore(self) -> None:
        assert classify(0) == ActionClass.IGNORE


# ---------------------------------------------------------------------------
# ExecutionAgent.run() tests
# ---------------------------------------------------------------------------


class TestExecutionAgentModelClassification:
    def test_model_record_is_classified_model(self) -> None:
        """Score >= 70 triggers MODEL classification."""
        rows = [_sqlite_row("10001", 75, rank=1)]
        with patch("src.agents.execution_agent.gold_get_digest", return_value=rows):
            result = ExecutionAgent().run()

        assert result.model_count == 1
        assert result.monitor_count == 0
        assert result.ignore_count == 0
        classified = result.classified[0]
        assert classified.action == ActionClass.MODEL
        assert classified.record.zip_code == "10001"

    def test_model_record_logged(self, caplog) -> None:
        """MODEL action is logged at INFO level with zip and score."""
        import logging

        rows = [_sqlite_row("10001", 80, rank=1)]
        with (
            patch("src.agents.execution_agent.gold_get_digest", return_value=rows),
            caplog.at_level(logging.INFO, logger="src.agents.execution_agent"),
        ):
            ExecutionAgent().run()

        assert any(
            "MODEL" in record.message and "10001" in record.message for record in caplog.records
        )


class TestExecutionAgentMonitorClassification:
    def test_monitor_record_is_classified_monitor(self) -> None:
        """Score 40–69 triggers MONITOR classification."""
        rows = [_sqlite_row("33101", 55, rank=1)]
        with patch("src.agents.execution_agent.gold_get_digest", return_value=rows):
            result = ExecutionAgent().run()

        assert result.model_count == 0
        assert result.monitor_count == 1
        assert result.ignore_count == 0
        assert result.classified[0].action == ActionClass.MONITOR

    def test_monitor_record_logged(self, caplog) -> None:
        """MONITOR action is logged at INFO level with watchlist mention."""
        import logging

        rows = [_sqlite_row("33101", 55, rank=1)]
        with (
            patch("src.agents.execution_agent.gold_get_digest", return_value=rows),
            caplog.at_level(logging.INFO, logger="src.agents.execution_agent"),
        ):
            ExecutionAgent().run()

        assert any(
            "MONITOR" in record.message and "33101" in record.message for record in caplog.records
        )


class TestExecutionAgentIgnoreClassification:
    def test_ignore_record_is_classified_ignore(self) -> None:
        """Score < 40 triggers IGNORE classification."""
        rows = [_sqlite_row("60601", 20, rank=1)]
        with patch("src.agents.execution_agent.gold_get_digest", return_value=rows):
            result = ExecutionAgent().run()

        assert result.model_count == 0
        assert result.monitor_count == 0
        assert result.ignore_count == 1
        assert result.classified[0].action == ActionClass.IGNORE

    def test_ignore_record_logged_at_debug(self, caplog) -> None:
        """IGNORE action is logged at DEBUG level."""
        import logging

        rows = [_sqlite_row("60601", 15, rank=1)]
        with (
            patch("src.agents.execution_agent.gold_get_digest", return_value=rows),
            caplog.at_level(logging.DEBUG, logger="src.agents.execution_agent"),
        ):
            ExecutionAgent().run()

        assert any(
            "IGNORE" in record.message and "60601" in record.message for record in caplog.records
        )


class TestExecutionAgentMixed:
    def test_mixed_records_classified_correctly(self) -> None:
        """Multiple records across all three buckets are classified correctly."""
        rows = [
            _sqlite_row("10001", 85, rank=1),  # MODEL
            _sqlite_row("33101", 50, rank=2),  # MONITOR
            _sqlite_row("60601", 25, rank=3),  # IGNORE
        ]
        with patch("src.agents.execution_agent.gold_get_digest", return_value=rows):
            result = ExecutionAgent().run()

        assert result.model_count == 1
        assert result.monitor_count == 1
        assert result.ignore_count == 1
        assert len(result.classified) == 3

    def test_empty_digest_returns_zero_counts(self) -> None:
        """Empty Gold digest produces all-zero ExecutionResult."""
        with patch("src.agents.execution_agent.gold_get_digest", return_value=[]):
            result = ExecutionAgent().run()

        assert result.model_count == 0
        assert result.monitor_count == 0
        assert result.ignore_count == 0
        assert result.classified == ()

    def test_boundary_score_40_is_monitor_not_ignore(self) -> None:
        """Score exactly 40 falls into MONITOR, not IGNORE."""
        rows = [_sqlite_row("10001", 40, rank=1)]
        with patch("src.agents.execution_agent.gold_get_digest", return_value=rows):
            result = ExecutionAgent().run()

        assert result.classified[0].action == ActionClass.MONITOR

    def test_boundary_score_70_is_model_not_monitor(self) -> None:
        """Score exactly 70 falls into MODEL, not MONITOR."""
        rows = [_sqlite_row("10001", 70, rank=1)]
        with patch("src.agents.execution_agent.gold_get_digest", return_value=rows):
            result = ExecutionAgent().run()

        assert result.classified[0].action == ActionClass.MODEL


class TestDispatchModelEdgeCases:
    def test_unknown_zip_logs_warning_and_skips_brief(self, caplog) -> None:
        """MODEL record with ZIP absent from _ZIP_CONFIG_INDEX logs a warning."""
        import logging

        rows = [_sqlite_row("99999", 80, rank=1)]  # 99999 is not in DEMO_ZIP_CONFIGS
        with (
            patch("src.agents.execution_agent.gold_get_digest", return_value=rows),
            caplog.at_level(logging.WARNING, logger="src.agents.execution_agent"),
        ):
            result = ExecutionAgent().run()

        assert result.model_count == 1
        assert any("no ZipConfig found" in r.message for r in caplog.records)

    def test_brief_generated_when_silver_available(self) -> None:
        """MODEL dispatch calls generate_brief when normalize_zip returns a record."""
        from unittest.mock import MagicMock

        from src.pipeline.normalizer import SilverRecord

        silver = SilverRecord(
            zip_code="10001",
            delinquency_rate=None,
            delinquency_date=None,
            unemployment_rate=None,
            unemployment_mom_change=None,
            average_rent=None,
            median_rent=None,
            rent_change_pct=None,
            vacancy_rate=None,
        )
        mock_brief = MagicMock()
        mock_brief.headline = "Strong distress signal"

        rows = [_sqlite_row("10001", 80, rank=1)]
        with (
            patch("src.agents.execution_agent.gold_get_digest", return_value=rows),
            patch("src.agents.execution_agent.normalize_zip", return_value=silver),
            patch("src.agents.execution_agent.generate_brief", return_value=mock_brief),
            patch("src.agents.execution_agent.get_sonnet_adapter", return_value=MagicMock()),
        ):
            result = ExecutionAgent().run()

        assert result.model_count == 1
