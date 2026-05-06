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
    # 7-signal expansion (optional — None if source not yet fetched)
    foreclosure_count: int | None = None
    price_index_change: float | None = None
    median_household_income: float | None = None
    hud_vacancy_rate: float | None = None


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


def _extract_attom_foreclosures(body: dict[str, object]) -> int | None:
    """Count property entries in ATTOM response — each is one foreclosure filing."""
    raw = body.get("property", [])
    if not isinstance(raw, list):
        return None
    return len(raw)


def _extract_fhfa_price_change(body: dict[str, object]) -> float | None:
    """Return QoQ % change between the two most-recent HPI data points."""
    raw = body.get("data", [])
    if not isinstance(raw, list) or len(raw) < 2:
        return None
    try:
        latest = float(str(raw[-1].get("index_sa", raw[-1].get("index", ""))))
        prior = float(str(raw[-2].get("index_sa", raw[-2].get("index", ""))))
        if prior == 0:
            return None
        return round((latest - prior) / prior * 100, 2)
    except (TypeError, ValueError):
        return None


def _extract_census_income(body: dict[str, object]) -> float | None:
    """Return median household income from ACS B19013_001E variable."""
    raw = body.get("B19013_001E")
    if raw is None:
        return None
    try:
        value = float(str(raw))
        return value if value > 0 else None
    except (TypeError, ValueError):
        return None


def _extract_hud_vacancy(body: dict[str, object]) -> float | None:
    """Return average business vacancy rate across all ZIP entries in the HUD response."""
    try:
        results = body.get("data", {})
        if not isinstance(results, dict):
            return None
        entries = results.get("results", [])
        if not isinstance(entries, list) or not entries:
            return None
        rates = [float(str(e["bus_ratio"])) for e in entries if "bus_ratio" in e]
        return round(sum(rates) / len(rates), 4) if rates else None
    except (TypeError, ValueError, KeyError):
        return None


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
    attom_days_back: int = 90,
    census_tract: str | None = None,
) -> SilverRecord | None:
    """Read Bronze for all available sources and return a SilverRecord.

    The three core sources (FRED, BLS, RentCast) are required — returns None
    if any are missing or stale.  The four extended sources (ATTOM, FHFA,
    Census, HUD) are optional and degrade gracefully to None.
    """
    fred_result = bronze_get_with_meta("fred", fred_series_id)
    bls_result = bronze_get_with_meta("bls", metro_code)
    rc_result = bronze_get_with_meta("rentcast", zip_code)

    for result in (fred_result, bls_result, rc_result):
        if result is None:
            return None
        _, fetched_at = result
        if not _is_fresh(fetched_at, max_age_days):
            return None

    # All three core results are guaranteed non-None after the loop above.
    assert fred_result is not None
    assert bls_result is not None
    assert rc_result is not None

    fred_data, _ = fred_result
    bls_data, _ = bls_result
    rc_data, _ = rc_result

    delinquency_rate, delinquency_date = _extract_fred(fred_data)
    unemployment_rate, unemployment_mom_change = _extract_bls(bls_data)

    # Extended sources — optional, no freshness gate.
    foreclosure_count: int | None = None
    attom_result = bronze_get_with_meta("attom", f"foreclosures:{zip_code}:{attom_days_back}")
    if attom_result is not None:
        foreclosure_count = _extract_attom_foreclosures(attom_result[0])

    price_index_change: float | None = None
    fhfa_result = bronze_get_with_meta("fhfa", f"price_index:{metro_code}")
    if fhfa_result is not None:
        price_index_change = _extract_fhfa_price_change(fhfa_result[0])

    median_household_income: float | None = None
    if census_tract is not None:
        census_result = bronze_get_with_meta("census", f"demographics:{census_tract}")
        if census_result is not None:
            median_household_income = _extract_census_income(census_result[0])

    hud_vacancy_rate: float | None = None
    hud_result = bronze_get_with_meta("hud", f"hud_vacancy:{metro_code}")
    if hud_result is not None:
        hud_vacancy_rate = _extract_hud_vacancy(hud_result[0])

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
        foreclosure_count=foreclosure_count,
        price_index_change=price_index_change,
        median_household_income=median_household_income,
        hud_vacancy_rate=hud_vacancy_rate,
    )
