"""End-to-end integration test for the full Phase B pipeline.

Covers: coordinator → score_zip_for_coordinator (mocked) → GoldRecords ranked
→ gold_upsert persisted → ExecutionAgent classifies → ActionClass labels correct.

Uses an isolated SQLite DB via CRE_DB_PATH env var override.
Delivery (SendGrid / Slack) is not exercised here — ExecutionAgent dispatches
to log-only stubs, which is fine for integration coverage.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents.coordinator import run_coordinator
from src.agents.execution_agent import ActionClass, ExecutionAgent
from src.pipeline.scorer import GoldRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NYC_CONFIGS = [
    {"zip_code": "10001", "metro_code": "LAUMT364002000000003", "fred_series_id": "DRSREACBS"},
    {"zip_code": "10014", "metro_code": "LAUMT364002000000003", "fred_series_id": "DRSREACBS"},
    {"zip_code": "11201", "metro_code": "LAUMT364002000000003", "fred_series_id": "DRSREACBS"},
]

_SCORES = {
    "10001": 72,  # MODEL
    "10014": 55,  # MONITOR
    "11201": 30,  # IGNORE
}


def _gold(zip_code: str) -> GoldRecord:
    score = _SCORES[zip_code]
    return GoldRecord(
        zip_code=zip_code,
        delinquency_score=score,
        employment_score=score,
        rent_vacancy_score=score,
        overall_score=score,
        rationale=f"integration test rationale for {zip_code}",
        rank=0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def _run(self, db_path: str) -> tuple[list[GoldRecord], object]:
        """Run coordinator then execution_agent against an isolated DB."""
        from src.pipeline._db import silver_upsert

        with patch.dict(os.environ, {"CRE_DB_PATH": db_path, "SCOPE_NYC_ONLY": "false"}):
            # Seed Silver rows to satisfy the gold_digest FK constraint.
            for cfg in _NYC_CONFIGS:
                silver_upsert(
                    zip_code=cfg["zip_code"],
                    delinquency_rate=3.5,
                    delinquency_date="2025-10-01",
                    unemployment_rate=5.0,
                    unemployment_mom_change=0.2,
                    average_rent=3000.0,
                    median_rent=2900.0,
                    rent_change_pct=-1.5,
                    vacancy_rate=6.0,
                )

            with patch(
                "src.agents.coordinator.score_zip_for_coordinator",
                side_effect=lambda cfg: _gold(cfg["zip_code"]),
            ):
                ranked = asyncio.run(run_coordinator(_NYC_CONFIGS))

            exec_result = ExecutionAgent().run()

        return ranked, exec_result

    def test_coordinator_produces_three_ranked_records(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            ranked, _ = self._run(path)
            assert len(ranked) == 3
            assert ranked[0].rank == 1
            assert ranked[1].rank == 2
            assert ranked[2].rank == 3
        finally:
            os.unlink(path)

    def test_records_sorted_by_overall_score_descending(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            ranked, _ = self._run(path)
            scores = [r.overall_score for r in ranked]
            assert scores == sorted(scores, reverse=True)
            assert ranked[0].zip_code == "10001"
            assert ranked[1].zip_code == "10014"
            assert ranked[2].zip_code == "11201"
        finally:
            os.unlink(path)

    def test_gold_records_persisted_to_db(self) -> None:
        from src.pipeline._db import gold_get_digest

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                self._run(path)
                rows = gold_get_digest()
            assert len(rows) == 3
            zip_codes = {row["zip_code"] for row in rows}
            assert zip_codes == {"10001", "10014", "11201"}
        finally:
            os.unlink(path)

    def test_execution_agent_classifies_all_three_labels(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            _, exec_result = self._run(path)
            assert exec_result.model_count == 1
            assert exec_result.monitor_count == 1
            assert exec_result.ignore_count == 1
        finally:
            os.unlink(path)

    def test_action_labels_match_scores(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            _, exec_result = self._run(path)
            classified_by_zip = {c.record.zip_code: c.action for c in exec_result.classified}
            assert classified_by_zip["10001"] == ActionClass.MODEL
            assert classified_by_zip["10014"] == ActionClass.MONITOR
            assert classified_by_zip["11201"] == ActionClass.IGNORE
        finally:
            os.unlink(path)

    def test_nyc_scope_filter_excludes_non_nyc(self) -> None:
        """With SCOPE_NYC_ONLY=true, non-NYC ZIPs are excluded."""
        from src.pipeline._db import silver_upsert

        non_nyc_configs = [
            {"zip_code": "33101", "metro_code": "METRO_X", "fred_series_id": "FRED_X"},
            {
                "zip_code": "10001",
                "metro_code": "LAUMT364002000000003",
                "fred_series_id": "DRSREACBS",
            },
        ]
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path, "SCOPE_NYC_ONLY": "true"}):
                silver_upsert(
                    zip_code="10001",
                    delinquency_rate=3.5,
                    delinquency_date="2025-10-01",
                    unemployment_rate=5.0,
                    unemployment_mom_change=0.2,
                    average_rent=3000.0,
                    median_rent=2900.0,
                    rent_change_pct=-1.5,
                    vacancy_rate=6.0,
                )
                with patch(
                    "src.agents.coordinator.score_zip_for_coordinator",
                    side_effect=lambda cfg: _gold(cfg["zip_code"]),
                ):
                    ranked = asyncio.run(run_coordinator(non_nyc_configs))
            assert len(ranked) == 1
            assert ranked[0].zip_code == "10001"
        finally:
            os.unlink(path)
