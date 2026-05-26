"""Backfill JSONL → SQLite. Idempotent, safe to re-run."""

from __future__ import annotations

from pathlib import Path

from cls_db.dual_write import make_dual_writer


def backfill_jsonl_to_db(
    jsonl_path: Path,
    db_path: Path,
    table: str,
    pk_field: str = "record_id",
    skip_existing: bool = True,
) -> dict:
    """Migrate JSONL records to SQLite.

    Returns {jsonl_count, db_count_before, db_count_after, inserted, skipped}
    """
    dw = make_dual_writer(jsonl_path, db_path, table, pk_field)

    db_count_before = dw.count_db()
    jsonl_records = dw.read_jsonl()

    existing_pks: set = set()
    if skip_existing:
        existing = dw.read_db(limit=None)
        existing_pks = {rec.get(pk_field) for rec in existing}

    to_insert = [r for r in jsonl_records if r.get(pk_field) not in existing_pks]

    if to_insert:
        dw.write_batch(to_insert)

    db_count_after = dw.count_db()

    return {
        "jsonl_count": len(jsonl_records),
        "db_count_before": db_count_before,
        "db_count_after": db_count_after,
        "inserted": len(to_insert),
        "skipped": len(jsonl_records) - len(to_insert),
    }


def verify_parity(jsonl_path: Path, db_path: Path, table: str) -> dict:
    """Check JSONL count == SQLite count.

    Returns {jsonl_count, db_count, parity, delta}
    """
    dw = make_dual_writer(jsonl_path, db_path, table)

    jsonl_count = dw.count_jsonl()
    db_count = dw.count_db()

    return {
        "jsonl_count": jsonl_count,
        "db_count": db_count,
        "parity": jsonl_count == db_count,
        "delta": jsonl_count - db_count,
    }
