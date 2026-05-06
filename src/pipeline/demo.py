"""Phase A demo orchestration helpers."""

from __future__ import annotations

import dataclasses

from src.llm.adapter import LLMAdapter
from src.mcp.bls import get_employment_trend
from src.mcp.fred import get_delinquency_rate
from src.mcp.rentcast import get_rent_trend, get_vacancy_rate
from src.pipeline._db import gold_upsert, silver_upsert
from src.pipeline.briefs import OpportunityBrief, generate_brief
from src.pipeline.normalizer import SilverRecord, normalize_zip
from src.pipeline.scorer import GoldRecord, build_digest, score_zip


@dataclasses.dataclass(frozen=True)
class DemoZipConfig:
    zip_code: str
    metro_code: str
    fred_series_id: str


@dataclasses.dataclass(frozen=True)
class DemoFailure:
    zip_code: str
    reason: str


@dataclasses.dataclass(frozen=True)
class DemoRunResult:
    digest: tuple[GoldRecord, ...]
    brief: OpportunityBrief | None
    failures: tuple[DemoFailure, ...]


DEMO_ZIP_CONFIGS: dict[str, DemoZipConfig] = {
    "10001": DemoZipConfig(
        zip_code="10001",
        metro_code="LAUMT363562000000003",
        fred_series_id="DRSREACBS",
    ),
    "33101": DemoZipConfig(
        zip_code="33101",
        metro_code="LAUMT123310000000003",
        fred_series_id="DRSREACBS",
    ),
    "60601": DemoZipConfig(
        zip_code="60601",
        metro_code="LAUMT171698000000003",
        fred_series_id="DRSREACBS",
    ),
    "90210": DemoZipConfig(
        zip_code="90210",
        metro_code="LAUMT063108000000004",
        fred_series_id="DRSREACBS",
    ),
}


def supported_demo_zips() -> tuple[str, ...]:
    return tuple(sorted(DEMO_ZIP_CONFIGS))


def parse_zips_argument(raw: str) -> list[str]:
    seen: set[str] = set()
    parsed: list[str] = []
    for part in raw.split(","):
        zip_code = part.strip()
        if not zip_code or zip_code in seen:
            continue
        seen.add(zip_code)
        parsed.append(zip_code)
    if not parsed:
        raise ValueError("At least one ZIP code is required via --zips.")
    return parsed


def resolve_demo_zips(zip_codes: list[str]) -> list[DemoZipConfig]:
    unsupported = [zip_code for zip_code in zip_codes if zip_code not in DEMO_ZIP_CONFIGS]
    if unsupported:
        supported = ", ".join(supported_demo_zips())
        joined = ", ".join(unsupported)
        raise ValueError(f"Unsupported ZIP code(s): {joined}. Supported demo ZIPs: {supported}")
    return [DEMO_ZIP_CONFIGS[zip_code] for zip_code in zip_codes]


def render_digest(records: tuple[GoldRecord, ...]) -> str:
    lines = [
        "## Ranked Digest",
        "Rank | ZIP | Overall | Delinq | Employ | Rent/Vac | Rationale",
    ]
    for record in records:
        lines.append(
            f"{record.rank} | {record.zip_code} | {record.overall_score} | "
            f"{record.delinquency_score} | {record.employment_score} | "
            f"{record.rent_vacancy_score} | {record.rationale}"
        )
    return "\n".join(lines)


def _persist_silver(record: SilverRecord) -> None:
    silver_upsert(
        zip_code=record.zip_code,
        delinquency_rate=record.delinquency_rate,
        delinquency_date=record.delinquency_date,
        unemployment_rate=record.unemployment_rate,
        unemployment_mom_change=record.unemployment_mom_change,
        average_rent=record.average_rent,
        median_rent=record.median_rent,
        rent_change_pct=record.rent_change_pct,
        vacancy_rate=record.vacancy_rate,
    )


def _persist_gold(record: GoldRecord) -> None:
    gold_upsert(
        zip_code=record.zip_code,
        delinquency_score=record.delinquency_score,
        employment_score=record.employment_score,
        rent_vacancy_score=record.rent_vacancy_score,
        overall_score=record.overall_score,
        rationale=record.rationale,
        rank=record.rank,
    )


def run_demo_for_zips(
    zip_codes: list[str],
    adapter: LLMAdapter | None = None,
) -> DemoRunResult:
    configs = resolve_demo_zips(zip_codes)
    if adapter is None:
        raise ValueError(
            "No LLM adapter provided. Phase B uses run_coordinator() from "
            "src.agents.coordinator — pass an explicit adapter or use the agent layer."
        )
    llm_adapter = adapter

    silver_by_zip: dict[str, SilverRecord] = {}
    gold_records: list[GoldRecord] = []
    failures: list[DemoFailure] = []

    for config in configs:
        try:
            get_delinquency_rate(config.fred_series_id)
            get_employment_trend(config.metro_code)
            get_rent_trend(config.zip_code)
            get_vacancy_rate(config.zip_code)

            silver_record = normalize_zip(
                zip_code=config.zip_code,
                metro_code=config.metro_code,
                fred_series_id=config.fred_series_id,
            )
            if silver_record is None:
                failures.append(
                    DemoFailure(
                        config.zip_code,
                        "Silver normalization failed due to missing or stale data.",
                    )
                )
                continue

            _persist_silver(silver_record)
            silver_by_zip[config.zip_code] = silver_record
            gold_records.append(score_zip(silver_record, llm_adapter))
        except Exception as exc:
            failures.append(DemoFailure(config.zip_code, str(exc)))

    ranked_digest = tuple(build_digest(gold_records))
    for gold_record in ranked_digest:
        _persist_gold(gold_record)

    brief: OpportunityBrief | None = None
    if ranked_digest:
        top_gold = ranked_digest[0]
        top_silver = silver_by_zip[top_gold.zip_code]
        brief = generate_brief(top_silver, top_gold, llm_adapter)

    return DemoRunResult(
        digest=ranked_digest,
        brief=brief,
        failures=tuple(failures),
    )
