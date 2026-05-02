"""Silver layer normalizer — reads Bronze, validates freshness, extracts signals."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

from src.mcp._db import bronze_get_with_meta


@dataclasses.dataclass(frozen=True)
class SilverRecord:
    zip_code: str
    delinquency_rate: float | None
    delinquency_date: str | None
    unemployment_rate: float | None
    unemployment_mom_change: float | None
    average_rent: float | None
    median_rent: float | None
    rent_change_pct: float | None
    vacancy_rate: float | None


def _is_fresh(fetched_at: str, max_age_days: int) -> bool:
    ts = datetime.fromisoformat(fetched_at)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    age = datetime.now(UTC) - ts
    return age.days <= max_age_days


def _extract_fred(
    body: dict[str, object],
) -> tuple[float | None, str | None]:
    raw = body.get("observations", [])
    observations: list[dict[str, object]] = raw if isinstance(raw, list) else []
    for obs in reversed(observations):
        value_str = str(obs.get("value", "."))
        if value_str != ".":
            date = obs.get("date")
            return float(value_str), str(date) if date is not None else None
    return None, None


def _extract_bls(
    body: dict[str, object],
) -> tuple[float | None, float | None]:
    try:
        results = body.get("Results", {})
        if not isinstance(results, dict):
            return None, None
        series_list = results.get("series", [])
        if not isinstance(series_list, list) or not series_list:
            return None, None
        first_series = series_list[0]
        if not isinstance(first_series, dict):
            return None, None
        data = first_series.get("data", [])
        if not isinstance(data, list) or not data:
            return None, None
        current = float(str(data[0].get("value", "")))
        mom_change = (current - float(str(data[1].get("value", "")))) if len(data) >= 2 else None
        return current, mom_change
    except (KeyError, IndexError, TypeError, ValueError):
        return None, None


def _opt_float(value: object) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def normalize_zip(
    zip_code: str,
    metro_code: str,
    fred_series_id: str,
    max_age_days: int = 30,
) -> SilverRecord | None:
    """Read Bronze for all 3 sources and return a SilverRecord, or None if data is missing/stale."""
    fred_result = bronze_get_with_meta("fred", fred_series_id)
    bls_result = bronze_get_with_meta("bls", metro_code)
    rc_result = bronze_get_with_meta("rentcast", zip_code)

    for result in (fred_result, bls_result, rc_result):
        if result is None:
            return None
        _, fetched_at = result
        if not _is_fresh(fetched_at, max_age_days):
            return None

    # All three results are guaranteed non-None after the loop above.
    assert fred_result is not None
    assert bls_result is not None
    assert rc_result is not None

    fred_data, _ = fred_result
    bls_data, _ = bls_result
    rc_data, _ = rc_result

    delinquency_rate, delinquency_date = _extract_fred(fred_data)
    unemployment_rate, unemployment_mom_change = _extract_bls(bls_data)

    return SilverRecord(
        zip_code=zip_code,
        delinquency_rate=delinquency_rate,
        delinquency_date=delinquency_date,
        unemployment_rate=unemployment_rate,
        unemployment_mom_change=unemployment_mom_change,
        average_rent=_opt_float(rc_data.get("averageRent")),
        median_rent=_opt_float(rc_data.get("medianRent")),
        rent_change_pct=_opt_float(rc_data.get("rentChangePercentage")),
        vacancy_rate=_opt_float(rc_data.get("vacancyRate")),
    )
