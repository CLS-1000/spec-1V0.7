"""Migration runner for cls_db SQLite schema."""
from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "db" / "migrations"


def run_migrations(db=None, migrations_dir=None):
    """Run all pending migrations in order. Returns count applied."""
    from cls_db.database import get_db
    db = db or get_db()
    mdir = migrations_dir or MIGRATIONS_DIR

    db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            filename   TEXT    NOT NULL UNIQUE,
            applied_at TEXT    NOT NULL DEFAULT (datetime('now')),
            checksum   TEXT    NOT NULL
        )
    """)

    applied = {
        row["filename"]
        for row in db.fetchall("SELECT filename FROM schema_migrations")
    }

    migration_files = sorted(mdir.glob("*.sql"))
    applied_count = 0

    for mf in migration_files:
        if mf.name in applied:
            logger.debug("Skipping: %s", mf.name)
            continue

        sql = mf.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode()).hexdigest()[:16]

        statements = re.split(r";\s*\n", sql)
        try:
            for stmt in statements:
                stmt = stmt.strip()
                lines = [
                    l for l in stmt.splitlines()
                    if l.strip() and not l.strip().startswith("--")
                ]
                if lines:
                    db.execute(stmt)

            db.execute(
                "INSERT INTO schema_migrations (filename, checksum) VALUES (?, ?)",
                (mf.name, checksum),
            )
            logger.info("Applied: %s", mf.name)
            applied_count += 1

        except Exception as exc:
            logger.error("Failed: %s — %s", mf.name, exc)
            raise

    logger.info("%d migration(s) applied", applied_count)
    return applied_count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
