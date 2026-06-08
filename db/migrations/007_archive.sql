-- Migration 007: archive layer — the graveyard
-- Dialect: SQLite
-- Nothing that enters this table ever leaves.
-- This is forensic storage, not a trash can.

CREATE TABLE IF NOT EXISTS archive (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    run_id          TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_type     TEXT NOT NULL,
    schema_version  INTEGER NOT NULL DEFAULT 1,

    -- Source record
    original_id     TEXT NOT NULL,
    origin_table    TEXT NOT NULL,

    -- Reason for archiving
    reason          TEXT NOT NULL CHECK (reason IN (
                        'score_below_threshold',
                        'superseded',
                        'fabrication_detected',
                        'signal_collapse',
                        'disclosure_gap',
                        'manual_review'
                    )),

    -- Full copy of the original record
    original_payload TEXT NOT NULL,

    -- Audit fields
    archived_at     TEXT NOT NULL DEFAULT (datetime('now')),
    archived_by     TEXT NOT NULL DEFAULT 'pipeline',
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_archive_run_id ON archive (run_id);
CREATE INDEX IF NOT EXISTS idx_archive_reason ON archive (reason);
CREATE INDEX IF NOT EXISTS idx_archive_origin_table ON archive (origin_table);
CREATE INDEX IF NOT EXISTS idx_archive_original_id ON archive (original_id);
CREATE INDEX IF NOT EXISTS idx_archive_archived_at ON archive (archived_at DESC);
