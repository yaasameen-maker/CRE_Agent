"""Coordinator agent — runs one sub-agent per ZIP in parallel via ThreadPoolExecutor.

Each worker is an independent scoring task (Pattern 3 loop): fetch Bronze →
normalize Silver → score Gold. Workers share the Bronze SQLite cache (safe —
_db.py opens a fresh connection per call) but each gets its own LLMAdapter
instance so adapters are not shared across threads.
"""

from __future__ import annotations

import dataclasses
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from src.llm import get_adapter
from src.mcp.bls import get_employment_trend
from src.mcp.fred import get_delinquency_rate
from src.mcp.rentcast import get_rent_trend, get_vacancy_rate
from src.pipeline._db import silver_upsert
from src.pipeline.demo import DEMO_ZIP_CONFIGS, DemoFailure, DemoZipConfig
from src.pipeline.normalizer import SilverRecord, normalize_zip
from src.pipeline.scorer import GoldRecord, build_digest, score_zip

_DEFAULT_MAX_WORKERS = 4


@dataclasses.dataclass(frozen=True)
class CoordinatorResult:
    digest: tuple[GoldRecord, ...]           # ranked by overall_score
    silver_map: dict[str, SilverRecord]      # zip_code → SilverRecord
    failures: tuple[DemoFailure, ...]


def _score_one_zip(
    config: DemoZipConfig,
) -> tuple[SilverRecord, GoldRecord] | DemoFailure:
    """Fetch, normalize, and score a single ZIP. Called inside a worker thread."""
    adapter = get_adapter()
    try:
        get_delinquency_rate(config.fred_series_id)
        get_employment_trend(config.metro_code)
        get_rent_trend(config.zip_code)
        get_vacancy_rate(config.zip_code)

        silver = normalize_zip(
            zip_code=config.zip_code,
            metro_code=config.metro_code,
            fred_series_id=config.fred_series_id,
        )
        if silver is None:
            return DemoFailure(
                config.zip_code,
                "Silver normalization failed due to missing or stale data.",
            )

        silver_upsert(
            zip_code=silver.zip_code,
            delinquency_rate=silver.delinquency_rate,
            delinquency_date=silver.delinquency_date,
            unemployment_rate=silver.unemployment_rate,
            unemployment_mom_change=silver.unemployment_mom_change,
            average_rent=silver.average_rent,
            median_rent=silver.median_rent,
            rent_change_pct=silver.rent_change_pct,
            vacancy_rate=silver.vacancy_rate,
        )
        return silver, score_zip(silver, adapter)
    except Exception as exc:
        return DemoFailure(config.zip_code, str(exc))


def run_coordinator(
    zip_codes: list[str],
    max_workers: int = _DEFAULT_MAX_WORKERS,
) -> CoordinatorResult:
    """Score all ZIP codes in parallel and return a ranked CoordinatorResult.

    Each ZIP runs in its own thread (I/O-bound: MCP API calls + LLM call).
    Raises ValueError for any unsupported ZIP code.
    """
    unsupported = [z for z in zip_codes if z not in DEMO_ZIP_CONFIGS]
    if unsupported:
        raise ValueError(f"Unsupported ZIP codes: {', '.join(unsupported)}")

    configs = [DEMO_ZIP_CONFIGS[z] for z in zip_codes]
    silver_map: dict[str, SilverRecord] = {}
    gold_records: list[GoldRecord] = []
    failures: list[DemoFailure] = []

    with ThreadPoolExecutor(max_workers=min(max_workers, len(configs))) as pool:
        future_to_zip: dict[Future[object], str] = {
            pool.submit(_score_one_zip, config): config.zip_code for config in configs
        }
        for future in as_completed(future_to_zip):
            result = future.result()
            if isinstance(result, DemoFailure):
                failures.append(result)
            else:
                silver, gold = result
                silver_map[silver.zip_code] = silver
                gold_records.append(gold)

    ranked = tuple(build_digest(gold_records))
    return CoordinatorResult(
        digest=ranked,
        silver_map=silver_map,
        failures=tuple(failures),
    )
