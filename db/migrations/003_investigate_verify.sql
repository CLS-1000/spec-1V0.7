-- Migration 003: investigate and verify layer
-- Dialect: SQLite

CREATE TABLE IF NOT EXISTS investigations (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id              TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    source_type         TEXT NOT NULL,
    schema_version      INTEGER NOT NULL DEFAULT 1,
    scored_signal_id    TEXT NOT NULL UNIQUE REFERENCES scored_signals(id),
    hypothesis          TEXT NOT NULL,
    queries             TEXT NOT NULL DEFAULT '[]',
    analyst_leads       TEXT NOT NULL DEFAULT '[]',
    sources_to_check    TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_inv_run_id ON investigations (run_id);
CREATE INDEX IF NOT EXISTS idx_inv_source_type ON investigations (source_type);

CREATE TABLE IF NOT EXISTS outcomes (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id              TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    source_type         TEXT NOT NULL,
    schema_version      INTEGER NOT NULL DEFAULT 1,
    investigation_id    TEXT NOT NULL UNIQUE REFERENCES investigations(id),
    classification      TEXT NOT NULL CHECK (classification IN (
                            'CORROBORATED','ESCALATE','INVESTIGATE',
                            'MONITOR','CONFLICTED','ARCHIVE')),
    confidence          REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    evidence            TEXT NOT NULL DEFAULT '[]',
    verified            INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (0,1)),
    reasoning           TEXT
);
CREATE INDEX IF NOT EXISTS idx_out_run_id ON outcomes (run_id);
CREATE INDEX IF NOT EXISTS idx_out_classification ON outcomes (classification);
CREATE INDEX IF NOT EXISTS idx_out_confidence ON outcomes (confidence DESC);

CREATE TABLE IF NOT EXISTS verification_log (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id              TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    source_type         TEXT NOT NULL DEFAULT 'llm',
    schema_version      INTEGER NOT NULL DEFAULT 1,
    outcome_id          TEXT NOT NULL REFERENCES outcomes(id),
    tier_used           TEXT NOT NULL CHECK (tier_used IN ('claude','ollama','mock')),
    model               TEXT,
    latency_ms          INTEGER,
    cost_estimate_usd   REAL DEFAULT 0.0,
    prompt_chars        INTEGER,
    response_chars      INTEGER,
    raw_response        TEXT
);
CREATE INDEX IF NOT EXISTS idx_vlog_run_id ON verification_log (run_id);
CREATE INDEX IF NOT EXISTS idx_vlog_tier ON verification_log (tier_used);
