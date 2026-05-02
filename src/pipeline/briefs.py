"""Opportunity brief generation for the Phase A demo."""

from __future__ import annotations

import dataclasses

from src.llm.adapter import LLMAdapter
from src.pipeline.normalizer import SilverRecord
from src.pipeline.scorer import GoldRecord
from src.prompts.briefing import BRIEF_SYSTEM_PROMPT

WRITE_OPPORTUNITY_BRIEF_TOOL: dict[str, object] = {
    "name": "write_opportunity_brief",
    "description": "Return a concise analyst-facing opportunity brief for one ZIP code.",
    "input_schema": {
        "type": "object",
        "properties": {
            "headline": {
                "type": "string",
                "description": "Single-sentence headline for the opportunity brief.",
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence summary of why the ZIP surfaced.",
            },
            "evidence_points": {
                "type": "array",
                "description": "3-5 short strings citing concrete values and sources.",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 5,
            },
            "watch_items": {
                "type": "array",
                "description": "2-3 short strings describing what to verify next.",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 3,
            },
        },
        "required": ["headline", "summary", "evidence_points", "watch_items"],
    },
}


@dataclasses.dataclass(frozen=True)
class OpportunityBrief:
    zip_code: str
    rank: int
    overall_score: int
    headline: str
    summary: str
    evidence_points: tuple[str, ...]
    watch_items: tuple[str, ...]


def _format_metric(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "data unavailable"
    return f"{value}{suffix}"


def _format_currency(value: float | None) -> str:
    if value is None:
        return "data unavailable"
    return f"${value:,.0f}"


def _build_user_message(silver_record: SilverRecord, gold_record: GoldRecord) -> str:
    return (
        f"ZIP code: {gold_record.zip_code}\n"
        f"Rank: {gold_record.rank}\n"
        f"Overall distress score: {gold_record.overall_score}\n"
        f"Gold rationale: {gold_record.rationale}\n"
        "\n"
        f"FRED delinquency rate: {_format_metric(silver_record.delinquency_rate, '%')}"
        f" (observation date: {silver_record.delinquency_date or 'data unavailable'})\n"
        f"BLS unemployment rate: {_format_metric(silver_record.unemployment_rate, '%')}\n"
        "BLS MoM unemployment change: "
        f"{_format_metric(silver_record.unemployment_mom_change, 'pp')}\n"
        f"RentCast average rent: {_format_currency(silver_record.average_rent)}\n"
        f"RentCast median rent: {_format_currency(silver_record.median_rent)}\n"
        f"RentCast 30-day rent change: {_format_metric(silver_record.rent_change_pct, '%')}\n"
        f"RentCast vacancy rate: {_format_metric(silver_record.vacancy_rate, '%')}\n"
        "\nWrite one opportunity brief using the write_opportunity_brief tool."
    )


def _require_tool_payload(
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


def _require_text_field(payload: dict[str, object], field: str) -> str:
    value = payload.get(field)
    if value is None:
        raise RuntimeError(f"write_opportunity_brief payload missing required field: {field}")
    text = str(value).strip()
    if not text:
        raise RuntimeError(f"write_opportunity_brief field {field} must be non-empty")
    return text


def _require_text_list(
    payload: dict[str, object],
    field: str,
    *,
    min_items: int,
    max_items: int,
) -> tuple[str, ...]:
    raw = payload.get(field)
    if not isinstance(raw, list):
        raise RuntimeError(f"write_opportunity_brief field {field} must be an array")
    values = tuple(str(item).strip() for item in raw if str(item).strip())
    if len(values) < min_items or len(values) > max_items:
        raise RuntimeError(
            f"write_opportunity_brief field {field} must contain {min_items}-{max_items} items"
        )
    return values


def generate_brief(
    silver_record: SilverRecord,
    gold_record: GoldRecord,
    adapter: LLMAdapter,
) -> OpportunityBrief:
    response = adapter.complete(
        messages=[{"role": "user", "content": _build_user_message(silver_record, gold_record)}],
        system=BRIEF_SYSTEM_PROMPT,
        tools=[WRITE_OPPORTUNITY_BRIEF_TOOL],
        tool_choice={"type": "tool", "name": "write_opportunity_brief"},
    )
    payload = _require_tool_payload(response.tool_calls, "write_opportunity_brief")
    return OpportunityBrief(
        zip_code=gold_record.zip_code,
        rank=gold_record.rank,
        overall_score=gold_record.overall_score,
        headline=_require_text_field(payload, "headline"),
        summary=_require_text_field(payload, "summary"),
        evidence_points=_require_text_list(
            payload,
            "evidence_points",
            min_items=3,
            max_items=5,
        ),
        watch_items=_require_text_list(payload, "watch_items", min_items=2, max_items=3),
    )


def render_brief(brief: OpportunityBrief) -> str:
    evidence = "\n".join(f"- {item}" for item in brief.evidence_points)
    watch_items = "\n".join(f"- {item}" for item in brief.watch_items)
    return (
        f"## Opportunity Brief: ZIP {brief.zip_code}\n"
        f"Rank: #{brief.rank} | Overall score: {brief.overall_score}\n\n"
        f"### Headline\n{brief.headline}\n\n"
        f"### Summary\n{brief.summary}\n\n"
        f"### Evidence\n{evidence}\n\n"
        f"### Watch Items\n{watch_items}"
    )
