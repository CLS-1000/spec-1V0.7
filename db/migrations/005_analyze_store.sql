-- Migration 005: analyze and store layer
-- Dialect: SQLite
-- Column list matches spec1_core pipeline output exactly

CREATE TABLE IF NOT EXISTS intelligence_records (
    id                    TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id                TEXT NOT NULL,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    source_type           TEXT NOT NULL DEFAULT 'pipeline',
    schema_version        INTEGER NOT NULL DEFAULT 1,

    -- Pipeline output fields (exact match to JSONL)
    record_id             TEXT NOT NULL UNIQUE,
    signal_id             TEXT,
    signal_source         TEXT NOT NULL,
    signal_url            TEXT,
    opportunity_id        TEXT,
    opportunity_score     REAL,
    opportunity_priority  TEXT,
    gate_results          TEXT DEFAULT '{}',
    investigation_id      TEXT,
    hypothesis            TEXT,
    outcome_classification TEXT,
    outcome_confidence    REAL,
    pattern               TEXT,
    classification        TEXT NOT NULL,
    confidence            REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    source_weight         REAL,
    analyst_weight        REAL,
    environment           TEXT NOT NULL DEFAULT 'production',
    written_at            TEXT
);

CREATE INDEX IF NOT EXISTS idx_ir_run_id          ON intelligence_records (run_id);
CREATE INDEX IF NOT EXISTS idx_ir_record_id       ON intelligence_records (record_id);
CREATE INDEX IF NOT EXISTS idx_ir_classification  ON intelligence_records (classification);
CREATE INDEX IF NOT EXISTS idx_ir_confidence      ON intelligence_records (confidence DESC);
CREATE INDEX IF NOT EXISTS idx_ir_signal_source   ON intelligence_records (signal_source);
CREATE INDEX IF NOT EXISTS idx_ir_priority        ON intelligence_records (opportunity_priority);

CREATE TABLE IF NOT EXISTS intelligence_store_log (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL DEFAULT 'pipeline',
    schema_version  INTEGER NOT NULL DEFAULT 1,
    records_written INTEGER NOT NULL DEFAULT 0,
    store_path      TEXT,
    completed_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_isl_run_id ON intelligence_store_log (run_id);
