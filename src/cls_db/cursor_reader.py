# @domain:   spec-1
# @module:   cursor_reader
# @loc:      gh_main
# @status:   stable
# @depends:  NONE

"""Cursor-based and chunked JSONL reading for cls_db.

Provides forward-only, stateless iteration over large JSONL files without
loading the entire file into memory.  A ``Cursor`` encodes the last-seen
(timestamp, record-id) pair so callers can resume where they left off across
separate requests.

Typical usage::

    reader = JSONLCursorReader(Path("spec1_intelligence.jsonl"))
    records, next_cursor = reader.read_chunk()       # first page
    while next_cursor:
        records, next_cursor = reader.read_chunk(cursor=next_cursor)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Tuple


@dataclass
class Cursor:
    """Opaque forward pagination token for JSONL files.

    The cursor stores the ``written_at`` timestamp, ``record_id``, and a byte
    offset into the file.  The byte offset allows :meth:`JSONLCursorReader.read_chunk`
    to seek directly to the correct position rather than scanning from the
    beginning on each page.  Use ``to_string()`` / ``from_string()`` to
    serialise/deserialise across HTTP or MCP calls.
    """

    start_ts: str
    start_id: str
    byte_offset: int = 0

    def to_string(self) -> str:
        """Serialise to a compact opaque string."""
        return f"{self.start_ts}|{self.start_id}|{self.byte_offset}"

    @classmethod
    def from_string(cls, token: str) -> "Cursor":
        """Deserialise from ``to_string()`` output.

        Accepts both the legacy two-part format (``ts|id``) for backward
        compatibility and the current three-part format (``ts|id|offset``).
        """
        if "|" not in token:
            raise ValueError(f"Invalid cursor token: {token!r}")
        parts = token.split("|", 2)
        if len(parts) == 2:
            # Legacy token without byte_offset — fall back to start of file.
            return cls(start_ts=parts[0], start_id=parts[1], byte_offset=0)
        try:
            offset = int(parts[2])
        except ValueError:
            offset = 0
        return cls(start_ts=parts[0], start_id=parts[1], byte_offset=offset)

    def __lt__(self, other: "Cursor") -> bool:
        return (self.start_ts, self.start_id) < (other.start_ts, other.start_id)


class JSONLCursorReader:
    """Read a JSONL file in forward-only chunks with cursor-based pagination.

    Parameters
    ----------
    path:
        Path to the JSONL file.
    chunk_size:
        Default number of records to return per chunk (overridable per call).
    ts_field:
        Field name holding the ISO-8601 timestamp used for cursor ordering.
        Falls back to ``written_at``.
    id_field:
        Field name holding the unique record identifier used as tie-breaker.
    """

    def __init__(
        self,
        path: Path,
        chunk_size: int = 1000,
        ts_field: str = "written_at",
        id_field: str = "record_id",
    ) -> None:
        self.path = Path(path)
        self.chunk_size = chunk_size
        self.ts_field = ts_field
        self.id_field = id_field

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_chunk(
        self,
        cursor: Optional[Cursor] = None,
        limit: Optional[int] = None,
    ) -> Tuple[list[dict], Optional[Cursor]]:
        """Return ``(records, next_cursor)``.

        Pass the returned ``next_cursor`` back on the next call to advance.
        Returns ``(records, None)`` on the final page.

        When *cursor* carries a ``byte_offset`` (all cursors produced by this
        method do), reading seeks directly to that file position — no O(n²)
        scan from the beginning.  Legacy cursor tokens without a byte offset
        (``byte_offset == 0``) fall back to reading from the start of the file.

        Parameters
        ----------
        cursor:
            If ``None``, reading starts from the beginning of the file.
            Otherwise, returns records that come *after* this cursor position.
        limit:
            Maximum number of records to return.  Defaults to
            ``self.chunk_size``.
        """
        effective_limit = limit if limit is not None else self.chunk_size
        if not self.path.exists():
            return [], None

        records: list[dict] = []
        last_offset: int = 0  # byte offset after the last collected record

        with self.path.open("r", encoding="utf-8") as fh:
            # Seek directly to the resume position when a valid byte offset is
            # available, avoiding a full-file scan on each page.
            if cursor is not None and cursor.byte_offset > 0:
                fh.seek(cursor.byte_offset)

            while len(records) < effective_limit:
                raw_line = fh.readline()
                if not raw_line:  # EOF
                    break
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                records.append(record)
                last_offset = fh.tell()

        if not records:
            return [], None

        last = records[-1]
        # If we received fewer records than requested, we've hit EOF — no next cursor.
        if len(records) < effective_limit:
            return records, None

        next_cursor = Cursor(
            start_ts=last.get(self.ts_field, ""),
            start_id=last.get(self.id_field, ""),
            byte_offset=last_offset,
        )
        return records, next_cursor

    def read_all_chunked(
        self, limit: Optional[int] = None
    ) -> Iterator[list[dict]]:
        """Yield successive chunks until the file is exhausted.

        Parameters
        ----------
        limit:
            Chunk size per iteration.  Defaults to ``self.chunk_size``.
        """
        cursor: Optional[Cursor] = None
        while True:
            records, cursor = self.read_chunk(cursor=cursor, limit=limit)
            if not records:
                break
            yield records
            if cursor is None:
                break

    def iter_records(self) -> Iterator[dict]:
        """Iterate every record one-by-one without loading all into memory."""
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def count(self) -> int:
        """Count total records without loading them."""
        return sum(1 for _ in self.iter_records())
