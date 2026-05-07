"""Append-only JSONL store for verdicts, with optional SQLite mirror via dual_write."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional

from cls_verdicts.schemas import Verdict


class VerdictStore:
    """Append-only JSONL store for human ground-truth verdicts.

    Multiple verdicts per record_id are permitted (annotator disagreement is preserved).
    """

    def __init__(self, jsonl_path: Path) -> None:
        self._path = Path(jsonl_path)
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, verdict: Verdict) -> None:
        """Append a single verdict to the store."""
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(verdict.to_dict()) + "\n")

    def read_all(self, limit: int = 500) -> list[Verdict]:
        """Return the last *limit* verdicts from the store."""
        if not self._path.exists():
            return []
        records: list[Verdict] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(Verdict.from_dict(json.loads(line)))
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        return records[-limit:]

    def read_for_record(self, record_id: str) -> list[Verdict]:
        """Return all verdicts for a specific record_id."""
        return [v for v in self.read_all(limit=10_000) if v.record_id == record_id]

    def count(self) -> int:
        """Return total number of verdicts in the store."""
        if not self._path.exists():
            return 0
        with self._path.open("r", encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())
