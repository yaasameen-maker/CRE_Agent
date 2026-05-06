-- Migration 003: expand Silver and Gold tables to 7-signal scoring.
-- Safe to run multiple times (ADD COLUMN IF NOT EXISTS).

ALTER TABLE silver_signals ADD COLUMN IF NOT EXISTS foreclosure_count        INTEGER;
ALTER TABLE silver_signals ADD COLUMN IF NOT EXISTS price_index_change       REAL;
ALTER TABLE silver_signals ADD COLUMN IF NOT EXISTS median_household_income  REAL;
ALTER TABLE silver_signals ADD COLUMN IF NOT EXISTS hud_vacancy_rate         REAL;

ALTER TABLE gold_digest    ADD COLUMN IF NOT EXISTS foreclosure_score        INTEGER NOT NULL DEFAULT 0;
ALTER TABLE gold_digest    ADD COLUMN IF NOT EXISTS price_score              INTEGER NOT NULL DEFAULT 0;
ALTER TABLE gold_digest    ADD COLUMN IF NOT EXISTS demographics_score       INTEGER NOT NULL DEFAULT 0;
ALTER TABLE gold_digest    ADD COLUMN IF NOT EXISTS hud_score                INTEGER NOT NULL DEFAULT 0;
