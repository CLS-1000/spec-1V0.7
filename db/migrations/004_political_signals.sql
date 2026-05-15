-- Migration 004: political_signals table
-- Dialect: SQLite (adapted from PostgreSQL spec for this deployment)
-- Append-only — no UPDATE or DELETE statements exist for this table.
-- Single writer: the /api/v1/ingest/signal endpoint.

CREATE TABLE IF NOT EXISTS political_signals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id     TEXT    UNIQUE NOT NULL,
    node_id       TEXT    NOT NULL,
    run_id        TEXT    NOT NULL,
    headline      TEXT    NOT NULL,
    summary       TEXT    NOT NULL,
    source_url    TEXT    NOT NULL,
    source_domain TEXT    NOT NULL,
    published_at  TEXT    NOT NULL,   -- UTC ISO-8601
    retrieved_at  TEXT    NOT NULL,   -- UTC ISO-8601
    gate_status   TEXT    NOT NULL,   -- 'PASS' | 'FAIL'
    gate_credibility REAL NOT NULL,
    gate_volume      REAL NOT NULL,
    gate_velocity    REAL NOT NULL,
    gate_novelty     REAL NOT NULL,
    signal_age_hours REAL NOT NULL,
    freshness_label  TEXT NOT NULL,   -- 'LIVE' | 'RECENT' | 'STALE'
    analyst_voice    TEXT,
    conflict_score   REAL,
    tags             TEXT DEFAULT '[]'  -- JSON array
);

CREATE INDEX IF NOT EXISTS idx_ps_node_id
    ON political_signals (node_id);

CREATE INDEX IF NOT EXISTS idx_ps_gate_status
    ON political_signals (gate_status);

CREATE INDEX IF NOT EXISTS idx_ps_published_at
    ON political_signals (published_at);

-- Composite index used by the hot query path (nodes endpoint)
CREATE INDEX IF NOT EXISTS idx_ps_node_gate_pub
    ON political_signals (node_id, gate_status, published_at);
