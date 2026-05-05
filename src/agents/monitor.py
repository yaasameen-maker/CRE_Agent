"""APScheduler monitor loop — triggers the full pipeline daily at 8am Eastern.

Cycle:
  1. Coordinator runs all ZIP codes in parallel (Pattern 3 sub-agents)
  2. Execution agent classifies Gold records and dispatches delivery
"""

from __future__ import annotations

import dataclasses

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.agents.coordinator import CoordinatorResult, run_coordinator
from src.agents.execution_agent import ExecutionResult, execute

MONITOR_ZIP_CODES: tuple[str, ...] = ("10001", "33101", "60601", "90210")


@dataclasses.dataclass(frozen=True)
class MonitorCycleResult:
    coordinator: CoordinatorResult
    execution: ExecutionResult


def run_daily_cycle() -> MonitorCycleResult:
    """Run one full Bronze → Silver → Gold → Execute cycle for all monitored ZIPs."""
    coordinator_result = run_coordinator(list(MONITOR_ZIP_CODES))
    execution_result = execute(
        digest=coordinator_result.digest,
        silver_map=coordinator_result.silver_map,
    )
    return MonitorCycleResult(
        coordinator=coordinator_result,
        execution=execution_result,
    )


def start_monitor(*, run_now: bool = False) -> None:
    """Start the blocking APScheduler daemon.

    Args:
        run_now: If True, execute one cycle immediately before the scheduler starts.
    """
    scheduler = BlockingScheduler(timezone="America/New_York")
    scheduler.add_job(run_daily_cycle, CronTrigger(hour=8, minute=0))
    if run_now:
        run_daily_cycle()
    scheduler.start()
