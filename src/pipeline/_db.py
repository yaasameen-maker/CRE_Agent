"""Silver and Gold pipeline DB helpers."""

from __future__ import annotations

import os
import sqlite3

_DEFAULT_DB_PATH = "data/cre_signal.db"


def _get_conn() -> sqlite3.Connection:
    path = os.getenv("CRE_DB_PATH", _DEFAULT_DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS silver_signals (
            zip_code                TEXT    PRIMARY KEY,
            delinquency_rate        REAL,
            delinquency_date        TEXT,
            unemployment_rate       REAL,
            unemployment_mom_change REAL,
            average_rent            REAL,
            median_rent             REAL,
            rent_change_pct         REAL,
            vacancy_rate            REAL,
            normalized_at           TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gold_digest (
            zip_code            TEXT    PRIMARY KEY REFERENCES silver_signals(zip_code),
            delinquency_score   INTEGER NOT NULL,
            employment_score    INTEGER NOT NULL,
            rent_vacancy_score  INTEGER NOT NULL,
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
) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO silver_signals (
                zip_code, delinquency_rate, delinquency_date,
                unemployment_rate, unemployment_mom_change,
                average_rent, median_rent, rent_change_pct, vacancy_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(zip_code) DO UPDATE SET
                delinquency_rate        = excluded.delinquency_rate,
                delinquency_date        = excluded.delinquency_date,
                unemployment_rate       = excluded.unemployment_rate,
                unemployment_mom_change = excluded.unemployment_mom_change,
                average_rent            = excluded.average_rent,
                median_rent             = excluded.median_rent,
                rent_change_pct         = excluded.rent_change_pct,
                vacancy_rate            = excluded.vacancy_rate,
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
) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO gold_digest (
                zip_code, delinquency_score, employment_score,
                rent_vacancy_score, overall_score, rationale, rank
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(zip_code) DO UPDATE SET
                delinquency_score   = excluded.delinquency_score,
                employment_score    = excluded.employment_score,
                rent_vacancy_score  = excluded.rent_vacancy_score,
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
