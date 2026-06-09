-- Migration 009: add psyop_scores, briefs, and verdicts tables

CREATE TABLE IF NOT EXISTS psyop_scores (
    score_id TEXT PRIMARY KEY,
    text_hash TEXT,
    text_excerpt TEXT,
    patterns_matched TEXT DEFAULT '[]',
    pattern_names TEXT DEFAULT '[]',
    score REAL DEFAULT 0.0,
    classification TEXT,
    threat_categories TEXT DEFAULT '[]',
    scored_at TEXT,
    metadata TEXT DEFAULT '{}',
    written_at TEXT
);

CREATE TABLE IF NOT EXISTS briefs (
    brief_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    headline TEXT,
    summary TEXT,
    sections TEXT DEFAULT '[]',
    sources TEXT DEFAULT '[]',
    confidence REAL DEFAULT 0.7,
    produced_at TEXT,
    metadata TEXT DEFAULT '{}',
    written_at TEXT
);

CREATE TABLE IF NOT EXISTS verdicts (
    verdict_id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL,
    verdict TEXT NOT NULL,
    reviewer TEXT DEFAULT 'anonymous',
    reviewed_at TEXT,
    notes TEXT DEFAULT '',
    written_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_verdicts_record_id ON verdicts(record_id);
