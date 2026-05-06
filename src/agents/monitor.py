"""APScheduler monitor — run the daily scoring cycle at 8am ET.

Usage:
    python -m src.agents.monitor          # Start the scheduler (blocking)
    python -m src.agents.monitor --once   # Run one cycle immediately and exit

run_daily_cycle() is also importable for ad-hoc manual triggers.
"""

from __future__ import annotations

import asyncio
import logging
import sys

logger = logging.getLogger(__name__)


def run_daily_cycle() -> None:
    """Execute one full scoring + delivery cycle.

    Steps:
    1. Load ZIP configs (DEMO_ZIP_CONFIGS for the Phase B demo).
    2. run_coordinator() — fan-out scoring, build digest, persist to Gold.
    3. ExecutionAgent().run() — classify and log delivery stubs.
    """
    from src.agents.coordinator import run_coordinator
    from src.agents.execution_agent import ExecutionAgent
    from src.agents.signal_agent import DEMO_ZIP_CONFIGS

    logger.info("daily cycle: starting")

    ranked = asyncio.run(run_coordinator(DEMO_ZIP_CONFIGS))
    logger.info("daily cycle: coordinator finished — %d ZIP codes ranked", len(ranked))

    result = ExecutionAgent().run()
    logger.info(
        "daily cycle: execution finished — MODEL=%d MONITOR=%d IGNORE=%d",
        result.model_count,
        result.monitor_count,
        result.ignore_count,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if "--once" in sys.argv:
        run_daily_cycle()
    else:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BlockingScheduler()
        scheduler.add_job(
            run_daily_cycle,
            CronTrigger(hour=8, minute=0, timezone="America/New_York"),
            id="daily_cycle",
            name="CRE Signal daily scoring cycle",
        )
        logger.info("scheduler: starting — will run at 08:00 ET every day")
        scheduler.start()
