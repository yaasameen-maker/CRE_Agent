"""Coordinator — fan-out scoring across all ZIP configs, build digest, persist to Gold.

Runs asynchronously: one score_zip_for_coordinator call per ZIP, gathered
concurrently with asyncio.  Failures are isolated — a failing ZIP does not
abort the whole run.
"""

from __future__ import annotations

import asyncio
import logging

from src.agents.signal_agent import ZipConfig, score_zip_for_coordinator
from src.pipeline._db import gold_upsert
from src.pipeline.config import SCOPE_NYC_ONLY, is_nyc_zip
from src.pipeline.scorer import GoldRecord, build_digest

logger = logging.getLogger(__name__)


async def _score_one(zip_config: ZipConfig) -> GoldRecord | None:
    """Run score_zip_for_coordinator in a thread pool so the event loop stays free."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, score_zip_for_coordinator, zip_config)


async def run_coordinator(zip_configs: list[ZipConfig]) -> list[GoldRecord]:
    """Score all ZIP configs concurrently, rank results, and upsert to Gold.

    Args:
        zip_configs: List of ZipConfig dicts describing each ZIP to score.

    Returns:
        Ranked list of GoldRecords (overall_score descending).  Empty ZIPs
        whose scoring returned None are silently excluded.
    """
    if not zip_configs:
        return []

    # Apply NYC scope filter if enabled.
    if SCOPE_NYC_ONLY:
        filtered = [cfg for cfg in zip_configs if is_nyc_zip(cfg["zip_code"])]
        skipped = len(zip_configs) - len(filtered)
        if skipped:
            logger.info("coordinator: skipped %d non-NYC ZIP(s) (SCOPE_NYC_ONLY=true)", skipped)
        zip_configs = filtered
        if not zip_configs:
            logger.warning("coordinator: no NYC ZIP codes remain after scope filter")
            return []

    # Fan-out: score every ZIP concurrently.
    results = await asyncio.gather(
        *(_score_one(cfg) for cfg in zip_configs),
        return_exceptions=True,
    )

    # Collect successful records; log failures.
    raw_records: list[GoldRecord] = []
    for cfg, result in zip(zip_configs, results, strict=False):
        zip_code = cfg["zip_code"]
        if isinstance(result, BaseException):
            logger.error("ZIP %s: unhandled exception during scoring: %s", zip_code, result)
        elif result is None:
            logger.warning("ZIP %s: scoring returned None — excluded from digest", zip_code)
        else:
            raw_records.append(result)

    if not raw_records:
        logger.warning("coordinator: no ZIP codes scored successfully")
        return []

    # Rank and persist.
    ranked = build_digest(raw_records)
    for record in ranked:
        gold_upsert(
            zip_code=record.zip_code,
            delinquency_score=record.delinquency_score,
            employment_score=record.employment_score,
            rent_vacancy_score=record.rent_vacancy_score,
            foreclosure_score=record.foreclosure_score,
            price_score=record.price_score,
            demographics_score=record.demographics_score,
            hud_score=record.hud_score,
            overall_score=record.overall_score,
            rationale=record.rationale,
            rank=record.rank,
        )

    logger.info(
        "coordinator: scored and ranked %d ZIP codes — run complete. "
        "Check per-call token logs above for spend breakdown.",
        len(ranked),
    )
    return ranked
