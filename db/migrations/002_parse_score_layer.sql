-- Migration 002: parse and score layer
-- Dialect: SQLite
CREATE TABLE IF NOT EXISTS parsed_signals (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL,
    schema_version  INTEGER NOT NULL DEFAULT 1,
    harvest_id      TEXT NOT NULL UNIQUE REFERENCES harvest_records(id),
    content_hash    TEXT NOT NULL,
    cleaned_text    TEXT NOT NULL,
    word_count      INTEGER NOT NULL DEFAULT 0,
    keywords        TEXT NOT NULL DEFAULT '[]',
    entities        TEXT NOT NULL DEFAULT '[]',
    language        TEXT NOT NULL DEFAULT 'en',
    parsed_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ps_run_id ON parsed_signals (run_id);
CREATE INDEX IF NOT EXISTS idx_ps_source_type ON parsed_signals (source_type);

CREATE TABLE IF NOT EXISTS scored_signals (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id              TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    source_type         TEXT NOT NULL,
    schema_version      INTEGER NOT NULL DEFAULT 1,
    parsed_signal_id    TEXT NOT NULL UNIQUE REFERENCES parsed_signals(id),
    harvest_id          TEXT NOT NULL REFERENCES harvest_records(id),
    content_hash        TEXT NOT NULL,
    score_credibility   REAL NOT NULL CHECK (score_credibility BETWEEN 0 AND 1),
    score_volume        REAL NOT NULL CHECK (score_volume BETWEEN 0 AND 1),
    score_velocity      REAL NOT NULL CHECK (score_velocity BETWEEN 0 AND 1),
    score_novelty       REAL NOT NULL CHECK (score_novelty BETWEEN 0 AND 1),
    gate_credibility    INTEGER NOT NULL DEFAULT 0 CHECK (gate_credibility IN (0,1)),
    gate_volume         INTEGER NOT NULL DEFAULT 0 CHECK (gate_volume IN (0,1)),
    gate_velocity       INTEGER NOT NULL DEFAULT 0 CHECK (gate_velocity IN (0,1)),
    gate_novelty        INTEGER NOT NULL DEFAULT 0 CHECK (gate_novelty IN (0,1)),
    composite_score     REAL NOT NULL CHECK (composite_score BETWEEN 0 AND 1),
    priority            TEXT NOT NULL CHECK (priority IN ('ELEVATED','STANDARD','MONITOR')),
    CHECK (gate_credibility=1 AND gate_volume=1 AND gate_velocity=1 AND gate_novelty=1)
);
CREATE INDEX IF NOT EXISTS idx_ss_run_id ON scored_signals (run_id);
CREATE INDEX IF NOT EXISTS idx_ss_priority ON scored_signals (priority);
CREATE INDEX IF NOT EXISTS idx_ss_composite ON scored_signals (composite_score DESC);

CREATE TABLE IF NOT EXISTS score_rejects (
    id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id              TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    source_type         TEXT NOT NULL,
    schema_version      INTEGER NOT NULL DEFAULT 1,
    parsed_signal_id    TEXT NOT NULL REFERENCES parsed_signals(id),
    harvest_id          TEXT NOT NULL REFERENCES harvest_records(id),
    content_hash        TEXT NOT NULL,
    score_credibility   REAL,
    score_volume        REAL,
    score_velocity      REAL,
    score_novelty       REAL,
    composite_score     REAL,
    gate_credibility    INTEGER,
    gate_volume         INTEGER,
    gate_velocity       INTEGER,
    gate_novelty        INTEGER,
    first_failure       TEXT CHECK (first_failure IN ('credibility','volume','velocity','novelty')),
    rejected_at         TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sr_run_id ON score_rejects (run_id);
CREATE INDEX IF NOT EXISTS idx_sr_first_failure ON score_rejects (first_failure);
