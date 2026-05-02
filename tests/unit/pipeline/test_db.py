"""Tests for Silver/Gold pipeline DB helpers."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch


def _make_temp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


class TestSilverUpsert:
    def test_insert_and_retrieve(self) -> None:
        path = _make_temp_db()
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                from src.pipeline._db import silver_get_all, silver_upsert

                silver_upsert(
                    zip_code="10001",
                    delinquency_rate=2.45,
                    delinquency_date="2025-10-01",
                    unemployment_rate=4.2,
                    unemployment_mom_change=-0.2,
                    average_rent=3200.0,
                    median_rent=3100.0,
                    rent_change_pct=-2.1,
                    vacancy_rate=4.2,
                )
                rows = silver_get_all()
                assert len(rows) == 1
                assert rows[0]["zip_code"] == "10001"
                assert rows[0]["delinquency_rate"] == 2.45
        finally:
            os.unlink(path)

    def test_upsert_replaces_existing(self) -> None:
        path = _make_temp_db()
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                from src.pipeline._db import silver_get_all, silver_upsert

                silver_upsert(
                    zip_code="10001",
                    delinquency_rate=2.45,
                    delinquency_date="2025-10-01",
                    unemployment_rate=4.2,
                    unemployment_mom_change=-0.2,
                    average_rent=3200.0,
                    median_rent=3100.0,
                    rent_change_pct=-2.1,
                    vacancy_rate=4.2,
                )
                silver_upsert(
                    zip_code="10001",
                    delinquency_rate=3.0,
                    delinquency_date="2026-01-01",
                    unemployment_rate=5.0,
                    unemployment_mom_change=0.8,
                    average_rent=3300.0,
                    median_rent=3200.0,
                    rent_change_pct=1.0,
                    vacancy_rate=5.5,
                )
                rows = silver_get_all()
                assert len(rows) == 1
                assert rows[0]["delinquency_rate"] == 3.0
        finally:
            os.unlink(path)

    def test_nullable_fields_accepted(self) -> None:
        path = _make_temp_db()
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                from src.pipeline._db import silver_get_all, silver_upsert

                silver_upsert(
                    zip_code="90210",
                    delinquency_rate=None,
                    delinquency_date=None,
                    unemployment_rate=None,
                    unemployment_mom_change=None,
                    average_rent=None,
                    median_rent=None,
                    rent_change_pct=None,
                    vacancy_rate=None,
                )
                rows = silver_get_all()
                assert rows[0]["delinquency_rate"] is None
        finally:
            os.unlink(path)


class TestGoldUpsert:
    def test_insert_and_get_digest(self) -> None:
        path = _make_temp_db()
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                from src.pipeline._db import gold_get_digest, gold_upsert, silver_upsert

                silver_upsert(
                    zip_code="10001",
                    delinquency_rate=2.45,
                    delinquency_date="2025-10-01",
                    unemployment_rate=4.2,
                    unemployment_mom_change=-0.2,
                    average_rent=3200.0,
                    median_rent=3100.0,
                    rent_change_pct=-2.1,
                    vacancy_rate=4.2,
                )
                gold_upsert(
                    zip_code="10001",
                    delinquency_score=70,
                    employment_score=55,
                    rent_vacancy_score=40,
                    overall_score=65,
                    rationale="High delinquency.",
                    rank=1,
                )
                rows = gold_get_digest()
                assert len(rows) == 1
                assert rows[0]["zip_code"] == "10001"
                assert rows[0]["overall_score"] == 65
                assert rows[0]["rank"] == 1
        finally:
            os.unlink(path)

    def test_digest_ordered_by_rank(self) -> None:
        path = _make_temp_db()
        try:
            with patch.dict(os.environ, {"CRE_DB_PATH": path}):
                from src.pipeline._db import gold_get_digest, gold_upsert, silver_upsert

                for zip_code, score, rank in [("10001", 80, 1), ("90210", 60, 2)]:
                    silver_upsert(
                        zip_code=zip_code,
                        delinquency_rate=None,
                        delinquency_date=None,
                        unemployment_rate=None,
                        unemployment_mom_change=None,
                        average_rent=None,
                        median_rent=None,
                        rent_change_pct=None,
                        vacancy_rate=None,
                    )
                    gold_upsert(
                        zip_code=zip_code,
                        delinquency_score=score,
                        employment_score=score,
                        rent_vacancy_score=score,
                        overall_score=score,
                        rationale="test",
                        rank=rank,
                    )
                rows = gold_get_digest()
                assert rows[0]["rank"] == 1
                assert rows[1]["rank"] == 2
        finally:
            os.unlink(path)
