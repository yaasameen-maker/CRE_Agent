"""Silver and Gold pipeline DB helpers."""

from __future__ import annotations

import os
import sqlite3

_DEFAULT_DB_PATH = "data/cre_signal.db"


def _migrate_gold_drop_fk(conn: sqlite3.Connection) -> None:
    """One-time migration: remove the FK constraint from gold_digest (schema v1 bug).

    The original schema had REFERENCES silver_signals(zip_code) on the PK, but
    the pipeline never writes Silver to the DB, so every gold_upsert() failed
    with FOREIGN KEY constraint failed.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='gold_digest'"
    ).fetchone()
    if row is None or "REFERENCES silver_signals" not in row[0]:
        return  # not yet created, or already migrated
    conn.execute("ALTER TABLE gold_digest RENAME TO _gold_digest_v1")
    conn.execute("""
        CREATE TABLE gold_digest (
            zip_code            TEXT    PRIMARY KEY,
            delinquency_score   INTEGER NOT NULL,
            employment_score    INTEGER NOT NULL,
            rent_vacancy_score  INTEGER NOT NULL,
            foreclosure_score   INTEGER NOT NULL DEFAULT 0,
            price_score         INTEGER NOT NULL DEFAULT 0,
            demographics_score  INTEGER NOT NULL DEFAULT 0,
            hud_score           INTEGER NOT NULL DEFAULT 0,
            overall_score       INTEGER NOT NULL,
            rationale           TEXT    NOT NULL,
            rank                INTEGER NOT NULL DEFAULT 0,
            scored_at           TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("INSERT INTO gold_digest SELECT * FROM _gold_digest_v1")
    conn.execute("DROP TABLE _gold_digest_v1")
    conn.commit()


def _migrate_silver_add_dob(conn: sqlite3.Connection) -> None:
    """One-time migration: add dob_violation_count column to silver_signals."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='silver_signals'"
    ).fetchone()
    if row is None or "dob_violation_count" in row[0]:
        return
    conn.execute("ALTER TABLE silver_signals ADD COLUMN dob_violation_count INTEGER")
    conn.commit()


def _get_conn() -> sqlite3.Connection:
    path = os.getenv("CRE_DB_PATH", _DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _migrate_gold_drop_fk(conn)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS silver_signals (
            zip_code                 TEXT    PRIMARY KEY,
            delinquency_rate         REAL,
            delinquency_date         TEXT,
            unemployment_rate        REAL,
            unemployment_mom_change  REAL,
            average_rent             REAL,
            median_rent              REAL,
            rent_change_pct          REAL,
            vacancy_rate             REAL,
            foreclosure_count        INTEGER,
            price_index_change       REAL,
            median_household_income  REAL,
            hud_vacancy_rate         REAL,
            dob_violation_count      INTEGER,
            normalized_at            TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    _migrate_silver_add_dob(conn)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gold_digest (
            zip_code            TEXT    PRIMARY KEY,
            delinquency_score   INTEGER NOT NULL,
            employment_score    INTEGER NOT NULL,
            rent_vacancy_score  INTEGER NOT NULL,
            foreclosure_score   INTEGER NOT NULL DEFAULT 0,
            price_score         INTEGER NOT NULL DEFAULT 0,
            demographics_score  INTEGER NOT NULL DEFAULT 0,
            hud_score           INTEGER NOT NULL DEFAULT 0,
            overall_score       INTEGER NOT NULL,
            rationale           TEXT    NOT NULL,
            rank                INTEGER NOT NULL DEFAULT 0,
            scored_at           TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def silver_upsert(
    *,
    zip_code: str,
    delinquency_rate: float | None,
    delinquency_date: str | None,
    unemployment_rate: float | None,
    unemployment_mom_change: float | None,
    average_rent: float | None,
    median_rent: float | None,
    rent_change_pct: float | None,
    vacancy_rate: float | None,
    foreclosure_count: int | None = None,
    price_index_change: float | None = None,
    median_household_income: float | None = None,
    hud_vacancy_rate: float | None = None,
    dob_violation_count: int | None = None,
) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO silver_signals (
                zip_code, delinquency_rate, delinquency_date,
                unemployment_rate, unemployment_mom_change,
                average_rent, median_rent, rent_change_pct, vacancy_rate,
                foreclosure_count, price_index_change,
                median_household_income, hud_vacancy_rate, dob_violation_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(zip_code) DO UPDATE SET
                delinquency_rate        = excluded.delinquency_rate,
                delinquency_date        = excluded.delinquency_date,
                unemployment_rate       = excluded.unemployment_rate,
                unemployment_mom_change = excluded.unemployment_mom_change,
                average_rent            = excluded.average_rent,
                median_rent             = excluded.median_rent,
                rent_change_pct         = excluded.rent_change_pct,
                vacancy_rate            = excluded.vacancy_rate,
                foreclosure_count       = excluded.foreclosure_count,
                price_index_change      = excluded.price_index_change,
                median_household_income = excluded.median_household_income,
                hud_vacancy_rate        = excluded.hud_vacancy_rate,
                dob_violation_count     = excluded.dob_violation_count,
                normalized_at           = datetime('now')
            """,
            (
                zip_code,
                delinquency_rate,
                delinquency_date,
                unemployment_rate,
                unemployment_mom_change,
                average_rent,
                median_rent,
                rent_change_pct,
                vacancy_rate,
                foreclosure_count,
                price_index_change,
                median_household_income,
                hud_vacancy_rate,
                dob_violation_count,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def silver_get_all() -> list[sqlite3.Row]:
    conn = _get_conn()
    try:
        return conn.execute("SELECT * FROM silver_signals").fetchall()
    finally:
        conn.close()


def gold_upsert(
    *,
    zip_code: str,
    delinquency_score: int,
    employment_score: int,
    rent_vacancy_score: int,
    overall_score: int,
    rationale: str,
    rank: int,
    foreclosure_score: int = 0,
    price_score: int = 0,
    demographics_score: int = 0,
    hud_score: int = 0,
) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO gold_digest (
                zip_code, delinquency_score, employment_score,
                rent_vacancy_score, foreclosure_score, price_score,
                demographics_score, hud_score, overall_score, rationale, rank
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(zip_code) DO UPDATE SET
                delinquency_score   = excluded.delinquency_score,
                employment_score    = excluded.employment_score,
                rent_vacancy_score  = excluded.rent_vacancy_score,
                foreclosure_score   = excluded.foreclosure_score,
                price_score         = excluded.price_score,
                demographics_score  = excluded.demographics_score,
                hud_score           = excluded.hud_score,
                overall_score       = excluded.overall_score,
                rationale           = excluded.rationale,
                rank                = excluded.rank,
                scored_at           = datetime('now')
            """,
            (
                zip_code,
                delinquency_score,
                employment_score,
                rent_vacancy_score,
                foreclosure_score,
                price_score,
                demographics_score,
                hud_score,
                overall_score,
                rationale,
                rank,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def gold_get_digest() -> list[sqlite3.Row]:
    conn = _get_conn()
    try:
        return conn.execute(
            "SELECT g.*, s.zip_code FROM gold_digest g "
            "JOIN silver_signals s ON s.zip_code = g.zip_code "
            "ORDER BY g.rank ASC"
        ).fetchall()
    finally:
        conn.close()


def gold_get_full() -> list[sqlite3.Row]:
    """Return gold scores joined with raw silver signal values for API responses."""
    conn = _get_conn()
    try:
        return conn.execute(
            """
            SELECT
                g.zip_code, g.overall_score, g.rank, g.rationale,
                g.delinquency_score, g.employment_score,
                g.rent_vacancy_score, g.foreclosure_score, g.price_score,
                g.scored_at,
                s.vacancy_rate, s.rent_change_pct, s.average_rent,
                s.unemployment_rate, s.unemployment_mom_change,
                s.foreclosure_count, s.price_index_change
            FROM gold_digest g
            JOIN silver_signals s ON s.zip_code = g.zip_code
            ORDER BY g.rank ASC
            """
        ).fetchall()
    finally:
        conn.close()
