"""Tests for the Gold scorer and digest builder."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.llm.adapter import LLMResponse
from src.pipeline.normalizer import SilverRecord


def _silver(
    zip_code: str = "10001",
    delinquency_rate: float | None = 2.45,
    unemployment_rate: float | None = 4.2,
    unemployment_mom_change: float | None = -0.2,
    vacancy_rate: float | None = 4.2,
    rent_change_pct: float | None = -2.1,
) -> SilverRecord:
    return SilverRecord(
        zip_code=zip_code,
        delinquency_rate=delinquency_rate,
        delinquency_date="2025-10-01",
        unemployment_rate=unemployment_rate,
        unemployment_mom_change=unemployment_mom_change,
        average_rent=3200.0,
        median_rent=3100.0,
        rent_change_pct=rent_change_pct,
        vacancy_rate=vacancy_rate,
    )


def _make_adapter(scores: dict[str, object]) -> MagicMock:
    adapter = MagicMock()
    adapter.complete.return_value = LLMResponse(
        content=None,
        tool_calls=(
            {
                "id": "tc_1",
                "name": "score_signals",
                "input": scores,
            },
        ),
        model="anthropic/claude-3-5-sonnet",
        stop_reason="tool_calls",
        usage={"prompt_tokens": 10, "completion_tokens": 5},
    )
    return adapter


class TestScoreZip:
    def test_returns_gold_record(self) -> None:
        from src.pipeline.scorer import GoldRecord, score_zip

        scores = {
            "delinquency_score": 45,
            "employment_score": 30,
            "rent_vacancy_score": 25,
            "overall_score": 35,
            "rationale": "Moderate delinquency.",
        }
        adapter = _make_adapter(scores)
        result = score_zip(_silver(), adapter)

        assert isinstance(result, GoldRecord)
        assert result.zip_code == "10001"
        assert result.delinquency_score == 45
        assert result.overall_score == 35
        assert result.rank == 0

    def test_calls_adapter_with_correct_tool(self) -> None:
        from src.pipeline.scorer import SCORE_SIGNALS_TOOL, score_zip

        adapter = _make_adapter(
            {
                "delinquency_score": 50,
                "employment_score": 40,
                "rent_vacancy_score": 30,
                "overall_score": 42,
                "rationale": "ok",
            }
        )
        score_zip(_silver(), adapter)

        call_kwargs = adapter.complete.call_args[1]
        assert call_kwargs["tools"] == [SCORE_SIGNALS_TOOL]
        assert call_kwargs["tool_choice"] == {"type": "tool", "name": "score_signals"}

    def test_reads_tool_calls_from_llm_response(self) -> None:
        from src.pipeline.scorer import score_zip

        adapter = _make_adapter(
            {
                "delinquency_score": 61,
                "employment_score": 55,
                "rent_vacancy_score": 40,
                "overall_score": 56,
                "rationale": "Uses real tool_calls payload.",
            }
        )
        result = score_zip(_silver(), adapter)
        assert result.overall_score == 56

    def test_silver_fields_included_in_user_message(self) -> None:
        from src.pipeline.scorer import score_zip

        adapter = _make_adapter(
            {
                "delinquency_score": 50,
                "employment_score": 40,
                "rent_vacancy_score": 30,
                "overall_score": 42,
                "rationale": "ok",
            }
        )
        record = _silver(zip_code="90210", delinquency_rate=3.8)
        score_zip(record, adapter)

        messages = adapter.complete.call_args[1]["messages"]
        user_content = messages[0]["content"]
        assert "90210" in user_content
        assert "3.8" in user_content

    def test_raises_on_missing_tool_use_block(self) -> None:
        import pytest
        from src.pipeline.scorer import score_zip

        adapter = MagicMock()
        adapter.complete.return_value = LLMResponse(
            content=None,
            tool_calls=(),
            model="anthropic/claude-3-5-sonnet",
            stop_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )

        with pytest.raises(RuntimeError, match="score_signals"):
            score_zip(_silver(), adapter)

    def test_raises_on_missing_required_score_field(self) -> None:
        import pytest
        from src.pipeline.scorer import score_zip

        adapter = _make_adapter(
            {
                "delinquency_score": 50,
                "employment_score": 40,
                "rent_vacancy_score": 30,
                "rationale": "missing overall score",
            }
        )
        with pytest.raises(RuntimeError, match="overall_score"):
            score_zip(_silver(), adapter)


class TestBuildDigest:
    def test_assigns_ranks_by_overall_score_descending(self) -> None:
        from src.pipeline.scorer import GoldRecord, build_digest

        records = [
            GoldRecord("10001", 40, 30, 25, 35, "low", rank=0),
            GoldRecord("90210", 70, 65, 60, 68, "high", rank=0),
            GoldRecord("33101", 55, 50, 45, 52, "mid", rank=0),
        ]
        ranked = build_digest(records)
        assert ranked[0].zip_code == "90210"
        assert ranked[0].rank == 1
        assert ranked[1].zip_code == "33101"
        assert ranked[1].rank == 2
        assert ranked[2].zip_code == "10001"
        assert ranked[2].rank == 3

    def test_original_records_unchanged(self) -> None:
        from src.pipeline.scorer import GoldRecord, build_digest

        records = [GoldRecord("10001", 40, 30, 25, 35, "test", rank=0)]
        build_digest(records)
        assert records[0].rank == 0

    def test_empty_list_returns_empty(self) -> None:
        from src.pipeline.scorer import build_digest

        assert build_digest([]) == []
