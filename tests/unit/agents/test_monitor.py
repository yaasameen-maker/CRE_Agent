"""Unit tests for src/agents/monitor.py."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from src.agents.monitor import MONITOR_ZIP_CODES, MonitorCycleResult, run_daily_cycle


def test_run_daily_cycle_calls_coordinator_with_monitor_zips() -> None:
    mock_coordinator_result = MagicMock()
    mock_coordinator_result.digest = ()
    mock_coordinator_result.silver_map = {}
    mock_execution_result = MagicMock()

    with (
        patch(
            "src.agents.monitor.run_coordinator", return_value=mock_coordinator_result
        ) as mock_coord,
        patch("src.agents.monitor.execute", return_value=mock_execution_result),
    ):
        result = run_daily_cycle()

    mock_coord.assert_called_once_with(list(MONITOR_ZIP_CODES))
    assert isinstance(result, MonitorCycleResult)


def test_run_daily_cycle_passes_digest_to_execution_agent() -> None:
    mock_gold = MagicMock()
    mock_silver_map = {"10001": MagicMock()}
    mock_coordinator_result = MagicMock()
    mock_coordinator_result.digest = (mock_gold,)
    mock_coordinator_result.silver_map = mock_silver_map
    mock_execution_result = MagicMock()

    with (
        patch("src.agents.monitor.run_coordinator", return_value=mock_coordinator_result),
        patch("src.agents.monitor.execute", return_value=mock_execution_result) as mock_exec,
    ):
        run_daily_cycle()

    mock_exec.assert_called_once_with(
        digest=(mock_gold,),
        silver_map=mock_silver_map,
    )


def test_start_monitor_run_now_triggers_cycle() -> None:
    mock_scheduler = MagicMock()

    with (
        patch("src.agents.monitor.BlockingScheduler", return_value=mock_scheduler),
        patch("src.agents.monitor.run_daily_cycle") as mock_cycle,
    ):
        from src.agents.monitor import start_monitor

        start_monitor(run_now=True)

    mock_cycle.assert_called_once()
    mock_scheduler.start.assert_called_once()


def test_start_monitor_no_run_now_skips_immediate_cycle() -> None:
    mock_scheduler = MagicMock()

    with (
        patch("src.agents.monitor.BlockingScheduler", return_value=mock_scheduler),
        patch("src.agents.monitor.run_daily_cycle") as mock_cycle,
    ):
        from src.agents.monitor import start_monitor

        start_monitor(run_now=False)

    mock_cycle.assert_not_called()
    mock_scheduler.start.assert_called_once()


def test_monitor_zip_codes_are_all_supported() -> None:
    from src.pipeline.demo import DEMO_ZIP_CONFIGS

    for zip_code in MONITOR_ZIP_CODES:
        assert zip_code in DEMO_ZIP_CONFIGS, f"{zip_code} not in DEMO_ZIP_CONFIGS"
