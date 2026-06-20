-- Migration 008: analyst workflow chain of custody
-- Dialect: SQLite
-- Append-only storage of analyst case files, outputs, audits, and verdicts

CREATE TABLE IF NOT EXISTS analyst_cases (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL DEFAULT 'analyst',
    schema_version  INTEGER NOT NULL DEFAULT 1,

    -- Case chain of custody
    case_id         TEXT NOT NULL UNIQUE,
    lead_id         TEXT NOT NULL,
    analyst_id      TEXT NOT NULL,

    -- Case content
    lead_text       TEXT NOT NULL,
    feed_prompt     TEXT NOT NULL,

    -- Metadata
    written_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_ac_run_id     ON analyst_cases (run_id);
CREATE INDEX IF NOT EXISTS idx_ac_case_id    ON analyst_cases (case_id);
CREATE INDEX IF NOT EXISTS idx_ac_lead_id    ON analyst_cases (lead_id);
CREATE INDEX IF NOT EXISTS idx_ac_analyst_id ON analyst_cases (analyst_id);
CREATE INDEX IF NOT EXISTS idx_ac_created_at ON analyst_cases (created_at DESC);

CREATE TABLE IF NOT EXISTS analyst_outputs (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL DEFAULT 'analyst',
    schema_version  INTEGER NOT NULL DEFAULT 1,

    -- Output chain of custody
    output_id       TEXT NOT NULL UNIQUE,
    case_id         TEXT NOT NULL REFERENCES analyst_cases(case_id),

    -- Output content
    raw_output      TEXT NOT NULL,
    source_data     TEXT,

    -- Metadata
    submitted_at    TEXT NOT NULL,
    written_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_ao_case_id    ON analyst_outputs (case_id);
CREATE INDEX IF NOT EXISTS idx_ao_output_id  ON analyst_outputs (output_id);
CREATE INDEX IF NOT EXISTS idx_ao_submitted_at ON analyst_outputs (submitted_at DESC);

CREATE TABLE IF NOT EXISTS audit_results (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL DEFAULT 'audit',
    schema_version  INTEGER NOT NULL DEFAULT 1,

    -- Audit chain of custody
    audit_id        TEXT NOT NULL UNIQUE,
    output_id       TEXT NOT NULL REFERENCES analyst_outputs(output_id),

    -- Audit metadata
    audit_llm       TEXT NOT NULL,
    audit_prompt    TEXT NOT NULL,

    -- Audit findings
    claims_confirmed INTEGER NOT NULL DEFAULT 0,
    claims_flagged   INTEGER NOT NULL DEFAULT 0,
    claims_dropped   INTEGER NOT NULL DEFAULT 0,
    audit_output    TEXT NOT NULL,
    confidence      REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),

    -- Metadata
    audited_at      TEXT NOT NULL,
    written_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_ar_audit_id   ON audit_results (audit_id);
CREATE INDEX IF NOT EXISTS idx_ar_output_id  ON audit_results (output_id);
CREATE INDEX IF NOT EXISTS idx_ar_audited_at ON audit_results (audited_at DESC);
CREATE INDEX IF NOT EXISTS idx_ar_confidence ON audit_results (confidence DESC);

CREATE TABLE IF NOT EXISTS analyst_verdicts (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL DEFAULT 'verdict',
    schema_version  INTEGER NOT NULL DEFAULT 1,

    -- Verdict chain of custody
    verdict_id      TEXT NOT NULL UNIQUE,
    case_id         TEXT NOT NULL REFERENCES analyst_cases(case_id),
    output_id       TEXT NOT NULL REFERENCES analyst_outputs(output_id),
    audit_id        TEXT REFERENCES audit_results(audit_id),

    -- Verdict content
    kind            TEXT NOT NULL CHECK (kind IN ('confirmed', 'partial', 'flagged', 'rejected')),
    reviewer        TEXT NOT NULL,
    notes           TEXT,
    published       INTEGER NOT NULL DEFAULT 0 CHECK (published IN (0, 1)),

    -- Metadata
    filed_at        TEXT NOT NULL,
    written_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_av_verdict_id ON analyst_verdicts (verdict_id);
CREATE INDEX IF NOT EXISTS idx_av_case_id    ON analyst_verdicts (case_id);
CREATE INDEX IF NOT EXISTS idx_av_output_id  ON analyst_verdicts (output_id);
CREATE INDEX IF NOT EXISTS idx_av_kind       ON analyst_verdicts (kind);
CREATE INDEX IF NOT EXISTS idx_av_published  ON analyst_verdicts (published);
CREATE INDEX IF NOT EXISTS idx_av_filed_at   ON analyst_verdicts (filed_at DESC);
