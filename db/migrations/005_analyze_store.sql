-- Migration 005: analyze and store layer
-- Dialect: SQLite

CREATE TABLE IF NOT EXISTS intelligence_records (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id              TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    source_type         TEXT NOT NULL,
    schema_version      INTEGER NOT NULL DEFAULT 1,
    outcome_id          TEXT NOT NULL UNIQUE REFERENCES outcomes(id),
    investigation_id    TEXT NOT NULL REFERENCES investigations(id),
    scored_signal_id    TEXT NOT NULL REFERENCES scored_signals(id),
    harvest_id          TEXT NOT NULL REFERENCES harvest_records(id),

    -- Final analysis output
    record_id           TEXT NOT NULL UNIQUE,
    pattern             TEXT NOT NULL,
    classification      TEXT NOT NULL,
    confidence          REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    source_weight       REAL NOT NULL CHECK (source_weight BETWEEN 0 AND 1),
    analyst_weight      REAL NOT NULL CHECK (analyst_weight BETWEEN 0 AND 1),

    -- Signal metadata
    signal_source       TEXT NOT NULL,
    signal_url          TEXT,
    opportunity_score   REAL,
    opportunity_priority TEXT,
    gate_results        TEXT DEFAULT '{}',
    hypothesis          TEXT,
    outcome_classification TEXT,
    outcome_confidence  REAL,
    environment         TEXT NOT NULL DEFAULT 'production'
);
CREATE INDEX IF NOT EXISTS idx_ir_run_id ON intelligence_records (run_id);
CREATE INDEX IF NOT EXISTS idx_ir_classification ON intelligence_records (classification);
CREATE INDEX IF NOT EXISTS idx_ir_confidence ON intelligence_records (confidence DESC);
CREATE INDEX IF NOT EXISTS idx_ir_signal_source ON intelligence_records (signal_source);
CREATE INDEX IF NOT EXISTS idx_ir_priority ON intelligence_records (opportunity_priority);

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
