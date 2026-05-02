-- Silver layer: one normalized row per ZIP code.
CREATE TABLE IF NOT EXISTS silver_signals (
    zip_code               TEXT    PRIMARY KEY,
    delinquency_rate       REAL,
    delinquency_date       TEXT,
    unemployment_rate      REAL,
    unemployment_mom_change REAL,
    average_rent           REAL,
    median_rent            REAL,
    rent_change_pct        REAL,
    vacancy_rate           REAL,
    normalized_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS gold_digest (
    zip_code           TEXT    PRIMARY KEY REFERENCES silver_signals(zip_code),
    delinquency_score  INTEGER NOT NULL,
    employment_score   INTEGER NOT NULL,
    rent_vacancy_score INTEGER NOT NULL,
    overall_score      INTEGER NOT NULL,
    rationale          TEXT    NOT NULL,
    rank               INTEGER NOT NULL DEFAULT 0,
    scored_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
