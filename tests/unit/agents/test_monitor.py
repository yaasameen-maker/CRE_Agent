"""Tests for src/agents/monitor.py."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch


class TestRunDailyCycle:
    def test_invokes_coordinator_and_execution_agent(self) -> None:
        """run_daily_cycle calls run_coordinator then ExecutionAgent().run()."""
        mock_ranked = [MagicMock()]
        mock_result = MagicMock()
        mock_result.model_count = 1
        mock_result.monitor_count = 0
        mock_result.ignore_count = 0

        async def fake_coordinator(_configs: list) -> list:
            return mock_ranked

        with (
            patch("src.agents.coordinator.run_coordinator", fake_coordinator),
            patch("src.agents.execution_agent.ExecutionAgent") as mock_agent_cls,
        ):
            mock_agent_cls.return_value.run.return_value = mock_result
            from src.agents.monitor import run_daily_cycle

            run_daily_cycle()

        mock_agent_cls.return_value.run.assert_called_once()

    def test_logs_coordinator_zip_count(self, caplog: object) -> None:
        """run_daily_cycle logs the number of ranked ZIPs from the coordinator."""
        mock_ranked = [MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.model_count = 0
        mock_result.monitor_count = 3
        mock_result.ignore_count = 0

        async def fake_coordinator(_configs: list) -> list:
            return mock_ranked

        with (
            patch("src.agents.coordinator.run_coordinator", fake_coordinator),
            patch("src.agents.execution_agent.ExecutionAgent") as mock_agent_cls,
            caplog.at_level(logging.INFO, logger="src.agents.monitor"),
        ):
            mock_agent_cls.return_value.run.return_value = mock_result
            from src.agents.monitor import run_daily_cycle

            run_daily_cycle()

        assert any("3" in r.message for r in caplog.records)
