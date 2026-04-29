-- Bronze layer: raw API response cache, one row per (source, cache_key).
CREATE TABLE IF NOT EXISTS bronze_cache (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source        TEXT    NOT NULL,   -- 'fred', 'bls', 'rentcast', etc.
    cache_key     TEXT    NOT NULL,   -- API-specific key (series_id, zip_code, etc.)
    response_json TEXT    NOT NULL,   -- Raw JSON blob from the API
    fetched_at    TEXT    NOT NULL    -- ISO 8601 UTC timestamp
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_bronze_source_key
    ON bronze_cache(source, cache_key);
