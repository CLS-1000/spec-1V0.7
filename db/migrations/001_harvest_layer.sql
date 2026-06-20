-- Migration 001: harvest layer
-- Dialect: SQLite
CREATE TABLE IF NOT EXISTS harvest_records (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL,
    schema_version  INTEGER NOT NULL DEFAULT 1,
    source_url      TEXT,
    source_name     TEXT NOT NULL,
    raw_content     TEXT,
    content_hash    TEXT NOT NULL UNIQUE,
    harvested_at    TEXT NOT NULL,
    fetch_status    INTEGER,
    payload_bytes   INTEGER,
    mime_type       TEXT
);
CREATE INDEX IF NOT EXISTS idx_hr_run_id ON harvest_records (run_id);
CREATE INDEX IF NOT EXISTS idx_hr_source_type ON harvest_records (source_type);
CREATE INDEX IF NOT EXISTS idx_hr_harvested_at ON harvest_records (harvested_at DESC);

CREATE TABLE IF NOT EXISTS harvest_runs (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT NOT NULL UNIQUE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL,
    schema_version  INTEGER NOT NULL DEFAULT 1,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    status          TEXT NOT NULL CHECK (status IN ('running','completed','failed','partial')),
    records_fetched INTEGER NOT NULL DEFAULT 0,
    records_new     INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT
);
CREATE INDEX IF NOT EXISTS idx_hruns_run_id ON harvest_runs (run_id);
CREATE INDEX IF NOT EXISTS idx_hruns_status ON harvest_runs (status);
