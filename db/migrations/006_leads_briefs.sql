-- Migration 006: leads and briefs layer
-- Dialect: SQLite

CREATE TABLE IF NOT EXISTS leads (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL DEFAULT 'pipeline',
    schema_version  INTEGER NOT NULL DEFAULT 1,
    lead_id         TEXT NOT NULL UNIQUE,
    intel_record_id TEXT REFERENCES intelligence_records(id),

    -- Lead content
    title           TEXT NOT NULL,
    summary         TEXT NOT NULL,
    priority        TEXT NOT NULL CHECK (priority IN ('HIGH','MEDIUM','LOW')),
    phase           INTEGER NOT NULL DEFAULT 1 CHECK (phase IN (1,2)),
    status          TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','ROUTED','PUBLISHED','SPIKED')),
    domain          TEXT,
    module          TEXT,
    recommended_adapter TEXT,
    investigative_lens  TEXT,
    freshness_window    TEXT,

    -- Feed prompt (the ignition point)
    context_load    TEXT,
    feed_prompt     TEXT,

    -- Confidence
    confidence      REAL CHECK (confidence BETWEEN 0 AND 1),
    confidence_label TEXT CHECK (confidence_label IN ('HIGH','MEDIUM','LOW'))
);
CREATE INDEX IF NOT EXISTS idx_leads_run_id ON leads (run_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads (status);
CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads (priority);
CREATE INDEX IF NOT EXISTS idx_leads_domain ON leads (domain);

CREATE TABLE IF NOT EXISTS world_state_briefs (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT NOT NULL UNIQUE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL DEFAULT 'pipeline',
    schema_version  INTEGER NOT NULL DEFAULT 1,
    brief_id        TEXT NOT NULL UNIQUE,
    brief_date      TEXT NOT NULL,
    issue_number    INTEGER,

    -- Content
    content_md      TEXT NOT NULL,
    word_count      INTEGER NOT NULL DEFAULT 0,
    executive_summary TEXT,
    elevated_count  INTEGER NOT NULL DEFAULT 0,
    domain_split    TEXT DEFAULT '{}',

    -- Output paths
    md_path         TEXT,
    pdf_path        TEXT,

    -- Generation metadata
    model_used      TEXT,
    generation_tier TEXT CHECK (generation_tier IN ('claude','ollama','mock','rule_based')),
    generated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_wsb_run_id ON world_state_briefs (run_id);
CREATE INDEX IF NOT EXISTS idx_wsb_brief_date ON world_state_briefs (brief_date DESC);
CREATE INDEX IF NOT EXISTS idx_wsb_issue ON world_state_briefs (issue_number DESC);

CREATE TABLE IF NOT EXISTS psycheops_columns (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL DEFAULT 'analyst',
    schema_version  INTEGER NOT NULL DEFAULT 1,
    column_id       TEXT NOT NULL UNIQUE,
    lead_id         TEXT REFERENCES leads(id),
    issue_number    INTEGER,

    -- Content
    title           TEXT NOT NULL,
    narrative_md    TEXT,
    report_md       TEXT,
    beat            TEXT DEFAULT '[]',
    priority        TEXT CHECK (priority IN ('HIGH','MEDIUM','LOW')),
    status          TEXT NOT NULL DEFAULT 'DRAFT' CHECK (
                        status IN ('DRAFT','REVIEWED','PUBLISHED')),

    -- Analyst
    analyst_id      TEXT,
    filed_at        TEXT,
    published_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_poc_run_id ON psycheops_columns (run_id);
CREATE INDEX IF NOT EXISTS idx_poc_status ON psycheops_columns (status);
CREATE INDEX IF NOT EXISTS idx_poc_issue ON psycheops_columns (issue_number DESC);
