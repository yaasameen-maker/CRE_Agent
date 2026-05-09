"""Gold layer scorer — LLM scoring via forced tool use."""

from __future__ import annotations

import dataclasses

from src.llm.adapter import LLMAdapter
from src.pipeline.normalizer import SilverRecord
from src.prompts.scoring import SCORING_SYSTEM_PROMPT

SCORE_SIGNALS_TOOL: dict[str, object] = {
    "name": "score_signals",
    "description": "Return distress scores for a single ZIP code.",
    "input_schema": {
        "type": "object",
        "properties": {
            "delinquency_score": {
                "type": "integer",
                "description": "Loan delinquency distress score 0-100.",
                "minimum": 0,
                "maximum": 100,
            },
            "employment_score": {
                "type": "integer",
                "description": "Employment distress score 0-100.",
                "minimum": 0,
                "maximum": 100,
            },
            "rent_vacancy_score": {
                "type": "integer",
                "description": "Rent/vacancy distress score 0-100.",
                "minimum": 0,
                "maximum": 100,
            },
            "foreclosure_score": {
                "type": "integer",
                "description": "Foreclosure filing distress score 0-100.",
                "minimum": 0,
                "maximum": 100,
            },
            "price_score": {
                "type": "integer",
                "description": "House price index trend distress score 0-100.",
                "minimum": 0,
                "maximum": 100,
            },
            "demographics_score": {
                "type": "integer",
                "description": "Demographic / income distress score 0-100.",
                "minimum": 0,
                "maximum": 100,
            },
            "hud_score": {
                "type": "integer",
                "description": "HUD commercial vacancy distress score 0-100.",
                "minimum": 0,
                "maximum": 100,
            },
            "overall_score": {
                "type": "integer",
                "description": "Weighted overall distress score 0-100.",
                "minimum": 0,
                "maximum": 100,
            },
            "rationale": {
                "type": "string",
                "description": "2-3 sentence explanation of dominant risk factors.",
            },
        },
        "required": [
            "delinquency_score",
            "employment_score",
            "rent_vacancy_score",
            "foreclosure_score",
            "price_score",
            "demographics_score",
            "hud_score",
            "overall_score",
            "rationale",
        ],
    },
}


@dataclasses.dataclass(frozen=True)
class GoldRecord:
    zip_code: str
    delinquency_score: int
    employment_score: int
    rent_vacancy_score: int
    overall_score: int
    rationale: str
    rank: int = 0
    foreclosure_score: int = 0
    price_score: int = 0
    demographics_score: int = 0
    hud_score: int = 0


def _find_tool_input(
    tool_calls: tuple[dict[str, object], ...],
    tool_name: str,
) -> dict[str, object]:
    for tool_call in tool_calls:
        if tool_call.get("name") != tool_name:
            continue
        payload = tool_call.get("input")
        if not isinstance(payload, dict):
            raise RuntimeError(f"{tool_name} returned a non-object payload: {payload!r}")
        return payload
    raise RuntimeError(f"LLM did not return a {tool_name} tool call.")


def _parse_score(scores: dict[str, object], field: str) -> int:
    if field not in scores:
        raise RuntimeError(f"score_signals payload missing required field: {field}")
    try:
        value = int(str(scores[field]))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"score_signals field {field} is not an integer: {scores[field]!r}"
        ) from exc
    if not 0 <= value <= 100:
        raise RuntimeError(f"score_signals field {field} must be between 0 and 100: {value}")
    return value


def _parse_rationale(scores: dict[str, object]) -> str:
    rationale = scores.get("rationale")
    if rationale is None:
        raise RuntimeError("score_signals payload missing required field: rationale")
    text = str(rationale).strip()
    if not text:
        raise RuntimeError("score_signals rationale must be non-empty")
    return text


def _build_user_message(record: SilverRecord) -> str:
    return (
        f"ZIP code: {record.zip_code}\n"
        f"Delinquency rate: {record.delinquency_rate} (date: {record.delinquency_date})\n"
        f"Unemployment rate: {record.unemployment_rate}%"
        f" (MoM change: {record.unemployment_mom_change}pp)\n"
        f"Average rent: ${record.average_rent}, median rent: ${record.median_rent}\n"
        f"Rent change (30-day): {record.rent_change_pct}%\n"
        f"Vacancy rate: {record.vacancy_rate}%\n"
        f"Foreclosure filings (90-day): {record.foreclosure_count}\n"
        f"Price index QoQ change: {record.price_index_change}%\n"
        f"Median household income: ${record.median_household_income}\n"
        f"HUD commercial vacancy rate: {record.hud_vacancy_rate}\n"
        f"DOB building violations (90-day): {record.dob_violation_count}\n"
        "\nScore this ZIP code using the score_signals tool."
    )


def score_zip(record: SilverRecord, adapter: LLMAdapter) -> GoldRecord:
    """Call the LLM with forced tool use and return a GoldRecord (rank=0)."""
    response = adapter.complete(
        messages=[{"role": "user", "content": _build_user_message(record)}],
        system=SCORING_SYSTEM_PROMPT,
        tools=[SCORE_SIGNALS_TOOL],
        tool_choice={"type": "tool", "name": "score_signals"},
    )
    scores = _find_tool_input(response.tool_calls, "score_signals")
    return GoldRecord(
        zip_code=record.zip_code,
        delinquency_score=_parse_score(scores, "delinquency_score"),
        employment_score=_parse_score(scores, "employment_score"),
        rent_vacancy_score=_parse_score(scores, "rent_vacancy_score"),
        foreclosure_score=_parse_score(scores, "foreclosure_score"),
        price_score=_parse_score(scores, "price_score"),
        demographics_score=_parse_score(scores, "demographics_score"),
        hud_score=_parse_score(scores, "hud_score"),
        overall_score=_parse_score(scores, "overall_score"),
        rationale=_parse_rationale(scores),
        rank=0,
    )


def build_digest(records: list[GoldRecord]) -> list[GoldRecord]:
    """Sort by overall_score descending and assign 1-based ranks. Returns new list."""
    sorted_records = sorted(records, key=lambda r: r.overall_score, reverse=True)
    return [dataclasses.replace(record, rank=i + 1) for i, record in enumerate(sorted_records)]
