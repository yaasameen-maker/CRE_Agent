"""Integration test for the Phase A demo pipeline."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import cast
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.llm.adapter import LLMAdapter, LLMResponse


def _make_temp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


class FakeAdapter(LLMAdapter):
    def complete(
        self,
        messages: list[dict[str, object]],
        system: str | list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
        tool_choice: dict[str, object] | None = None,
    ) -> LLMResponse:
        _ = system
        _ = tools
        user_message = cast(str, messages[0]["content"])
        tool_name = cast(str, tool_choice["name"]) if tool_choice is not None else ""

        if tool_name == "score_signals":
            zip_code = "10001" if "ZIP code: 10001" in user_message else "33101"
            overall_score = 72 if zip_code == "10001" else 58
            return LLMResponse(
                content=None,
                tool_calls=(
                    {
                        "id": f"score_{zip_code}",
                        "name": "score_signals",
                        "input": {
                            "delinquency_score": 75 if zip_code == "10001" else 55,
                            "employment_score": 68 if zip_code == "10001" else 48,
                            "rent_vacancy_score": 60 if zip_code == "10001" else 44,
                            "foreclosure_score": 50,
                            "price_score": 45,
                            "demographics_score": 40,
                            "hud_score": 35,
                            "overall_score": overall_score,
                            "rationale": f"Scored {zip_code} for integration coverage.",
                        },
                    },
                ),
                model="anthropic/claude-3-5-sonnet",
                stop_reason="tool_calls",
                usage={"prompt_tokens": 10, "completion_tokens": 5},
            )

        return LLMResponse(
            content=None,
            tool_calls=(
                {
                    "id": "brief_10001",
                    "name": "write_opportunity_brief",
                    "input": {
                        "headline": "ZIP 10001 is leading the current distress screen.",
                        "summary": (
                            "Employment and delinquency both deteriorated enough to "
                            "push this ZIP to the top of the digest. Rent softness "
                            "reinforces the need for a tighter market review."
                        ),
                        "evidence_points": [
                            "FRED delinquency is elevated for the shared real estate loan series.",
                            "BLS unemployment for the mapped metro is moving higher.",
                            "RentCast shows weakening rent momentum for the ZIP.",
                        ],
                        "watch_items": [
                            "Confirm whether distress is concentrated in one property subtype.",
                            (
                                "Check whether leasing concessions are widening faster "
                                "than headline rents."
                            ),
                        ],
                    },
                },
            ),
            model="anthropic/claude-3-5-sonnet",
            stop_reason="tool_calls",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )


def test_run_demo_pipeline_persists_silver_and_gold_and_generates_brief() -> None:
    from src.mcp._db import bronze_set
    from src.pipeline._db import gold_get_digest, silver_get_all
    from src.pipeline.briefs import render_brief
    from src.pipeline.demo import run_demo_for_zips

    path = _make_temp_db()
    try:
        with patch.dict(os.environ, {"CRE_DB_PATH": path}):
            with patch("src.pipeline.demo.get_delinquency_rate") as mock_fred:
                with patch("src.pipeline.demo.get_employment_trend") as mock_bls:
                    with patch("src.pipeline.demo.get_rent_trend") as mock_rent:
                        with patch("src.pipeline.demo.get_vacancy_rate") as mock_vacancy:

                            def _seed_fred(series_id: str) -> dict[str, object]:
                                data = {
                                    "observations": [
                                        {"date": "2025-10-01", "value": "3.8"},
                                    ]
                                }
                                bronze_set("fred", series_id, data)
                                return data

                            def _seed_bls(metro_code: str) -> dict[str, object]:
                                values = {
                                    "LAUMT363562000000003": ("5.2", "4.8"),
                                    "LAUMT123310000000003": ("4.4", "4.1"),
                                }
                                current, prior = values[metro_code]
                                data = {
                                    "Results": {
                                        "series": [
                                            {
                                                "data": [
                                                    {"value": current},
                                                    {"value": prior},
                                                ]
                                            }
                                        ]
                                    }
                                }
                                bronze_set("bls", metro_code, data)
                                return data

                            def _seed_rent(zip_code: str) -> dict[str, object]:
                                values = {
                                    "10001": {
                                        "averageRent": 3200.0,
                                        "medianRent": 3100.0,
                                        "rentChangePercentage": -2.1,
                                        "vacancyRate": 7.0,
                                    },
                                    "33101": {
                                        "averageRent": 2800.0,
                                        "medianRent": 2700.0,
                                        "rentChangePercentage": -0.8,
                                        "vacancyRate": 5.5,
                                    },
                                }
                                data = values[zip_code]
                                bronze_set("rentcast", zip_code, data)
                                return data

                            mock_fred.side_effect = _seed_fred
                            mock_bls.side_effect = _seed_bls
                            mock_rent.side_effect = _seed_rent
                            mock_vacancy.side_effect = _seed_rent

                            result = run_demo_for_zips(["10001", "33101"], adapter=FakeAdapter())

            assert len(result.failures) == 0
            assert len(result.digest) == 2
            assert result.digest[0].zip_code == "10001"
            assert result.digest[0].rank == 1
            assert result.brief is not None
            assert "ZIP 10001" in render_brief(result.brief)

            silver_rows = silver_get_all()
            gold_rows = gold_get_digest()
            assert len(silver_rows) == 2
            assert len(gold_rows) == 2
            assert gold_rows[0]["zip_code"] == "10001"
            assert gold_rows[0]["rank"] == 1
    finally:
        os.unlink(path)
