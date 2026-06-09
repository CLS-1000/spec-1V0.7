-- Migration 009: capture tables created outside migration stack

CREATE TABLE IF NOT EXISTS signals (
    signal_id    TEXT PRIMARY KEY,
    source       TEXT NOT NULL,
    source_type  TEXT NOT NULL DEFAULT 'rss',
    text         TEXT,
    url          TEXT,
    author       TEXT,
    published_at TEXT,
    velocity     REAL DEFAULT 0.0,
    engagement   REAL DEFAULT 0.0,
    run_id       TEXT,
    environment  TEXT DEFAULT 'production',
    metadata     TEXT DEFAULT '{}',
    written_at   TEXT
);

CREATE TABLE IF NOT EXISTS briefs (
    brief_id    TEXT PRIMARY KEY,
    date        TEXT NOT NULL,
    headline    TEXT,
    summary     TEXT,
    sections    TEXT DEFAULT '[]',
    sources     TEXT DEFAULT '[]',
    confidence  REAL DEFAULT 0.7,
    produced_at TEXT,
    metadata    TEXT DEFAULT '{}',
    written_at  TEXT
);

CREATE TABLE IF NOT EXISTS psyop_scores (
    score_id          TEXT PRIMARY KEY,
    text_hash         TEXT,
    text_excerpt      TEXT,
    patterns_matched  TEXT DEFAULT '[]',
    pattern_names     TEXT DEFAULT '[]',
    score             REAL DEFAULT 0.0,
    classification    TEXT,
    threat_categories TEXT DEFAULT '[]',
    scored_at         TEXT,
    metadata          TEXT DEFAULT '{}',
    written_at        TEXT
);

CREATE TABLE IF NOT EXISTS verdicts (
    verdict_id  TEXT PRIMARY KEY,
    record_id   TEXT NOT NULL,
    verdict     TEXT NOT NULL,
    reviewer    TEXT DEFAULT 'anonymous',
    reviewed_at TEXT,
    notes       TEXT DEFAULT '',
    written_at  TEXT
);

CREATE TABLE IF NOT EXISTS congress_records (
    record_id   TEXT PRIMARY KEY,
    record_type TEXT,
    bill_id     TEXT,
    title       TEXT,
    sponsor     TEXT,
    chamber     TEXT,
    status      TEXT,
    date        TEXT,
    summary     TEXT,
    url         TEXT,
    tags        TEXT DEFAULT '[]',
    metadata    TEXT DEFAULT '{}',
    written_at  TEXT
);

CREATE TABLE IF NOT EXISTS fara_records (
    record_id           TEXT PRIMARY KEY,
    registrant          TEXT NOT NULL,
    foreign_principal   TEXT,
    country             TEXT,
    activities          TEXT DEFAULT '[]',
    filed_at            TEXT,
    doc_url             TEXT,
    registration_number TEXT DEFAULT '',
    status              TEXT DEFAULT 'active',
    metadata            TEXT DEFAULT '{}',
    written_at          TEXT
);

CREATE TABLE IF NOT EXISTS intel_records (
    record_id       TEXT PRIMARY KEY,
    pattern         TEXT,
    classification  TEXT,
    confidence      REAL DEFAULT 0.0,
    source_weight   REAL DEFAULT 0.0,
    analyst_weight  REAL DEFAULT 0.0,
    run_id          TEXT,
    written_at      TEXT
);

CREATE TABLE IF NOT EXISTS osint_records (
    record_id    TEXT PRIMARY KEY,
    source_type  TEXT NOT NULL,
    source_name  TEXT,
    content      TEXT,
    url          TEXT,
    collected_at TEXT,
    metadata     TEXT DEFAULT '{}',
    written_at   TEXT
);
