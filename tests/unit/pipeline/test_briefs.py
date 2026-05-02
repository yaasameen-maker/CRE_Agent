"""Tests for Phase A opportunity brief generation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from src.llm.adapter import LLMResponse
from src.pipeline.briefs import OpportunityBrief
from src.pipeline.normalizer import SilverRecord
from src.pipeline.scorer import GoldRecord


def _silver() -> SilverRecord:
    return SilverRecord(
        zip_code="10001",
        delinquency_rate=3.8,
        delinquency_date="2025-10-01",
        unemployment_rate=5.2,
        unemployment_mom_change=0.4,
        average_rent=3200.0,
        median_rent=3100.0,
        rent_change_pct=-2.1,
        vacancy_rate=7.0,
    )


def _gold() -> GoldRecord:
    return GoldRecord(
        zip_code="10001",
        delinquency_score=70,
        employment_score=62,
        rent_vacancy_score=58,
        overall_score=64,
        rationale="Delinquency and labor softening are both elevated.",
        rank=1,
    )


def _make_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.complete.return_value = LLMResponse(
        content=None,
        tool_calls=(
            {
                "id": "tc_1",
                "name": "write_opportunity_brief",
                "input": {
                    "headline": "Mounting labor softness is widening distress in ZIP 10001.",
                    "summary": (
                        "The ZIP screened to the top because employment softened while "
                        "delinquency stayed elevated. Rent trends are also weakening "
                        "enough to support a closer underwriting pass."
                    ),
                    "evidence_points": [
                        "FRED shows a 3.8% delinquency rate as of 2025-10-01.",
                        "BLS unemployment reached 5.2%, up 0.4pp month over month.",
                        "RentCast shows rents down 2.1% over 30 days.",
                    ],
                    "watch_items": [
                        (
                            "Verify whether recent delinquency stress is concentrated in "
                            "office exposure."
                        ),
                        (
                            "Check if lease-up concessions are rising faster than "
                            "asking-rent declines."
                        ),
                    ],
                },
            },
        ),
        model="anthropic/claude-3-5-sonnet",
        stop_reason="tool_calls",
        usage={"prompt_tokens": 10, "completion_tokens": 5},
    )
    return adapter


class TestGenerateBrief:
    def test_returns_opportunity_brief(self) -> None:
        from src.pipeline.briefs import generate_brief

        result = generate_brief(_silver(), _gold(), _make_adapter())
        assert isinstance(result, OpportunityBrief)
        assert result.zip_code == "10001"
        assert result.rank == 1
        assert result.overall_score == 64
        assert len(result.evidence_points) == 3
        assert len(result.watch_items) == 2

    def test_calls_adapter_with_forced_tool_choice(self) -> None:
        from src.pipeline.briefs import WRITE_OPPORTUNITY_BRIEF_TOOL, generate_brief

        adapter = _make_adapter()
        generate_brief(_silver(), _gold(), adapter)

        kwargs = adapter.complete.call_args[1]
        assert kwargs["tools"] == [WRITE_OPPORTUNITY_BRIEF_TOOL]
        assert kwargs["tool_choice"] == {"type": "tool", "name": "write_opportunity_brief"}

    def test_missing_tool_call_raises(self) -> None:
        from src.pipeline.briefs import generate_brief

        adapter = MagicMock()
        adapter.complete.return_value = LLMResponse(
            content=None,
            tool_calls=(),
            model="anthropic/claude-3-5-sonnet",
            stop_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        with pytest.raises(RuntimeError, match="write_opportunity_brief"):
            generate_brief(_silver(), _gold(), adapter)


class TestRenderBrief:
    def test_markdown_contains_sections(self) -> None:
        from src.pipeline.briefs import render_brief

        brief = OpportunityBrief(
            zip_code="10001",
            rank=1,
            overall_score=64,
            headline="Headline",
            summary="Summary",
            evidence_points=("Point A", "Point B", "Point C"),
            watch_items=("Watch A", "Watch B"),
        )
        rendered = render_brief(brief)
        assert "## Opportunity Brief: ZIP 10001" in rendered
        assert "### Evidence" in rendered
        assert "- Point A" in rendered
        assert "### Watch Items" in rendered
