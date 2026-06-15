# @domain:   spec-1
# @module:   db_signals
# @loc:      gh_main
# @status:   stable
# @depends:  spec1_core, cls_db

"""Async-safe SQLite queries for the political_signals table.

All public functions are async; they delegate synchronous work to a
thread via asyncio.to_thread so the FastAPI event loop is never blocked.
The underlying connection is the shared cls_db.database.Database instance.

Invariants enforced here:
  - No UPDATE or DELETE statements — append-only
  - All datetimes stored as UTC ISO-8601 text
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

from cls_db.database import get_db


# ── Internal sync workers ─────────────────────────────────────────────────────

def _fetch_latest(node_id: str) -> Optional[dict]:
    db = get_db()
    return db.fetchone(
        """
        SELECT *
        FROM political_signals
        WHERE node_id = ? AND gate_status = 'PASS'
        ORDER BY published_at DESC
        LIMIT 1
        """,
        (node_id,),
    )


def _fetch_prior_summaries(node_id: str, n: int) -> list[str]:
    db = get_db()
    rows = db.fetchall(
        """
        SELECT summary
        FROM political_signals
        WHERE node_id = ? AND gate_status = 'PASS'
        ORDER BY published_at DESC
        LIMIT ?
        """,
        (node_id, n),
    )
    return [r["summary"] for r in rows]


def _insert(data: dict) -> bool:
    """INSERT OR IGNORE. Returns True if the row was written, False if it already existed."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT OR IGNORE INTO political_signals
                (signal_id, node_id, run_id, headline, summary,
                 source_url, source_domain, published_at, retrieved_at,
                 gate_status, gate_credibility, gate_volume,
                 gate_velocity, gate_novelty, signal_age_hours,
                 freshness_label, analyst_voice, conflict_score, tags)
            VALUES
                (?, ?, ?, ?, ?,
                 ?, ?, ?, ?,
                 ?, ?, ?,
                 ?, ?, ?,
                 ?, ?, ?, ?)
            """,
            (
                data["signal_id"],
                data["node_id"],
                data["run_id"],
                data["headline"],
                data["summary"],
                data["source_url"],
                data["source_domain"],
                data["published_at"],
                data["retrieved_at"],
                data["gate_status"],
                data["gate_credibility"],
                data["gate_volume"],
                data["gate_velocity"],
                data["gate_novelty"],
                data["signal_age_hours"],
                data["freshness_label"],
                data.get("analyst_voice"),
                data.get("conflict_score"),
                json.dumps(data.get("tags", [])),
            ),
        )
        return cur.rowcount > 0


# ── Public async API ──────────────────────────────────────────────────────────

async def get_latest_signal_for_node(node_id: str) -> Optional[dict]:
    """Return the most-recent PASS signal row for *node_id*, or None."""
    return await asyncio.to_thread(_fetch_latest, node_id)


async def get_prior_summaries(node_id: str, n: int = 20) -> list[str]:
    """Return up to *n* most-recent PASS summaries for *node_id* (for novelty scoring)."""
    return await asyncio.to_thread(_fetch_prior_summaries, node_id, n)


async def insert_signal(data: dict) -> bool:
    """INSERT OR IGNORE a signal row. Returns True if written, False if duplicate."""
    return await asyncio.to_thread(_insert, data)
