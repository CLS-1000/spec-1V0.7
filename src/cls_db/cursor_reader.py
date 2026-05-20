"""Cursor-based pagination for append-only JSONL stores.

Stateless pagination: resume from (timestamp, id) tuple.
Memory-bounded: never materializes full file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


@dataclass
class Cursor:
    """Pagination marker: (written_at_ts, record_id)"""
    start_ts: str
    start_id: str

    def to_string(self) -> str:
        return f"{self.start_ts}|{self.start_id}"

    @classmethod
    def from_string(cls, s: str) -> "Cursor":
        ts, rid = s.split("|", 1)
        return cls(start_ts=ts, start_id=rid)


class JSONLCursorReader:
    """Chunked JSONL reader with cursor-based pagination."""

    def __init__(self, path: Path, chunk_size: int = 1000):
        self.path = Path(path)
        self.chunk_size = chunk_size

    def read_chunk(
        self,
        cursor: Optional[Cursor] = None,
        limit: int = 100,
    ) -> tuple[list[dict], Optional[Cursor]]:
        """Read next chunk of records from JSONL.

        Args:
            cursor: Resume from this point, or None for start
            limit: Max records per chunk

        Returns:
            (records, next_cursor) where next_cursor=None at EOF
        """
        records: list[dict] = []
        next_cursor: Optional[Cursor] = None

        if not self.path.exists():
            return [], None

        seen_cursor_pos = cursor is None

        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not seen_cursor_pos:
                    rec_ts = record.get("written_at", "")
                    rec_id = record.get("record_id", "")
                    if (rec_ts, rec_id) > (cursor.start_ts, cursor.start_id):
                        seen_cursor_pos = True
                    else:
                        continue

                records.append(record)

                if len(records) >= limit:
                    next_cursor = Cursor(
                        start_ts=record.get("written_at", ""),
                        start_id=record.get("record_id", ""),
                    )
                    break

        return records, next_cursor

    def read_all_chunked(self, limit: int = 100) -> Iterator[list[dict]]:
        """Yield chunks without loading entire file."""
        cursor: Optional[Cursor] = None
        while True:
            chunk, cursor = self.read_chunk(cursor, limit)
            if not chunk:
                break
            yield chunk
