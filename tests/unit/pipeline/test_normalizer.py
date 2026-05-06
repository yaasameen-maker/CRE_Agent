"""Tests for the Silver normalizer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch


def _ts(days_ago: int = 0) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()


def _fred_body(value: str = "2.45", date: str = "2025-10-01") -> dict:  # type: ignore[type-arg]
    return {
        "observations": [
            {"date": date, "value": value},
        ]
    }


def _bls_body(current: str = "4.2", prior: str = "4.4") -> dict:  # type: ignore[type-arg]
    return {
        "status": "REQUEST_SUCCEEDED",
        "Results": {
            "series": [
                {
                    "seriesID": "LAUMT060310000000003",
                    "data": [
                        {"year": "2025", "period": "M12", "value": current},
                        {"year": "2025", "period": "M11", "value": prior},
                    ],
                }
            ]
        },
    }


def _rentcast_body(vacancy: float = 4.2, rent_change: float = -2.1) -> dict:  # type: ignore[type-arg]
    return {
        "averageRent": 3200.0,
        "medianRent": 3100.0,
        "vacancyRate": vacancy,
        "rentChangePercentage": rent_change,
    }


class TestIsFresh:
    def test_fresh_returns_true(self) -> None:
        from src.pipeline.normalizer import _is_fresh

        assert _is_fresh(_ts(days_ago=5), max_age_days=30) is True

    def test_stale_returns_false(self) -> None:
        from src.pipeline.normalizer import _is_fresh

        assert _is_fresh(_ts(days_ago=31), max_age_days=30) is False

    def test_exactly_at_boundary_returns_true(self) -> None:
        from src.pipeline.normalizer import _is_fresh

        assert _is_fresh(_ts(days_ago=30), max_age_days=30) is True


class TestExtractFred:
    def test_extracts_most_recent_non_null(self) -> None:
        from src.pipeline.normalizer import _extract_fred

        body = {
            "observations": [
                {"date": "2025-07-01", "value": "2.38"},
                {"date": "2025-10-01", "value": "2.45"},
            ]
        }
        value, date = _extract_fred(body)
        assert value == 2.45
        assert date == "2025-10-01"

    def test_skips_dot_null(self) -> None:
        from src.pipeline.normalizer import _extract_fred

        body = {
            "observations": [
                {"date": "2025-07-01", "value": "2.38"},
                {"date": "2025-10-01", "value": "."},
            ]
        }
        value, date = _extract_fred(body)
        assert value == 2.38
        assert date == "2025-07-01"

    def test_all_null_returns_none_tuple(self) -> None:
        from src.pipeline.normalizer import _extract_fred

        body = {"observations": [{"date": "2025-10-01", "value": "."}]}
        value, date = _extract_fred(body)
        assert value is None
        assert date is None

    def test_empty_observations_returns_none_tuple(self) -> None:
        from src.pipeline.normalizer import _extract_fred

        value, date = _extract_fred({"observations": []})
        assert value is None
        assert date is None


class TestExtractBls:
    def test_returns_current_rate_and_mom_change(self) -> None:
        from src.pipeline.normalizer import _extract_bls

        rate, change = _extract_bls(_bls_body("4.2", "4.4"))
        assert rate == 4.2
        assert abs(change - (-0.2)) < 0.001

    def test_single_data_point_mom_change_is_none(self) -> None:
        from src.pipeline.normalizer import _extract_bls

        body = {"Results": {"series": [{"data": [{"value": "4.2"}]}]}}
        rate, change = _extract_bls(body)
        assert rate == 4.2
        assert change is None

    def test_empty_series_returns_none_tuple(self) -> None:
        from src.pipeline.normalizer import _extract_bls

        body = {"Results": {"series": []}}
        rate, change = _extract_bls(body)
        assert rate is None
        assert change is None


class TestNormalizeZip:
    def test_returns_silver_record_on_fresh_data(self) -> None:
        from src.pipeline.normalizer import SilverRecord, normalize_zip

        fred_meta = (_fred_body(), _ts(days_ago=1))
        bls_meta = (_bls_body(), _ts(days_ago=1))
        rc_meta = (_rentcast_body(), _ts(days_ago=1))

        with patch("src.pipeline.normalizer.bronze_get_with_meta") as mock_get:
            # 3 required + 3 optional (attom, fhfa, hud); no census_tract so no census call
            mock_get.side_effect = [fred_meta, bls_meta, rc_meta, None, None, None]
            result = normalize_zip(
                zip_code="10001",
                metro_code="LAUMT060310000000003",
                fred_series_id="DRSREACBS",
            )

        assert isinstance(result, SilverRecord)
        assert result.zip_code == "10001"
        assert result.delinquency_rate == 2.45
        assert result.unemployment_rate == 4.2
        assert result.average_rent == 3200.0

    def test_returns_none_on_missing_bronze(self) -> None:
        from src.pipeline.normalizer import normalize_zip

        with patch("src.pipeline.normalizer.bronze_get_with_meta", return_value=None):
            result = normalize_zip(
                zip_code="10001",
                metro_code="LAUMT060310000000003",
                fred_series_id="DRSREACBS",
            )
        assert result is None

    def test_returns_none_on_stale_data(self) -> None:
        from src.pipeline.normalizer import normalize_zip

        stale_ts = _ts(days_ago=45)
        fred_meta = (_fred_body(), stale_ts)

        with patch("src.pipeline.normalizer.bronze_get_with_meta") as mock_get:
            mock_get.side_effect = [fred_meta, None, None]
            result = normalize_zip(
                zip_code="10001",
                metro_code="LAUMT060310000000003",
                fred_series_id="DRSREACBS",
            )
        assert result is None

    def test_null_fred_observation_stored_as_none(self) -> None:
        from src.pipeline.normalizer import normalize_zip

        fred_body = {"observations": [{"date": "2025-10-01", "value": "."}]}
        bls_meta = (_bls_body(), _ts(days_ago=1))
        rc_meta = (_rentcast_body(), _ts(days_ago=1))

        with patch("src.pipeline.normalizer.bronze_get_with_meta") as mock_get:
            # 3 required + 3 optional (attom, fhfa, hud)
            mock_get.side_effect = [
                (fred_body, _ts(days_ago=1)),
                bls_meta,
                rc_meta,
                None,
                None,
                None,
            ]
            result = normalize_zip(
                zip_code="10001",
                metro_code="LAUMT060310000000003",
                fred_series_id="DRSREACBS",
            )
        assert result is not None
        assert result.delinquency_rate is None
