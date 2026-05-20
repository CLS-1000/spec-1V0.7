"""Fast indexed queries on SQLite backend."""

from __future__ import annotations

from cls_db.repository import Repository, _row_to_dict


class IndexedQueryLayer:
    """Query via SQLite indexes."""

    def __init__(self, repo: Repository):
        self.repo = repo
        self.table = repo.table

    def find_by_source(self, source: str, limit: int = 100) -> list[dict]:
        """Filter by source_type."""
        query = f"SELECT * FROM {self.table} WHERE source_type = ? ORDER BY written_at DESC LIMIT ?"
        rows = self.repo.db.fetchall(query, (source, limit))
        return [_row_to_dict(r) for r in rows]

    def find_by_status(self, status: str, limit: int = 100) -> list[dict]:
        """Filter by status."""
        query = f"SELECT * FROM {self.table} WHERE status = ? ORDER BY written_at DESC LIMIT ?"
        rows = self.repo.db.fetchall(query, (status, limit))
        return [_row_to_dict(r) for r in rows]

    def find_by_signal_type(self, signal_type: str, limit: int = 100) -> list[dict]:
        """Filter by signal_type."""
        query = f"SELECT * FROM {self.table} WHERE signal_type = ? ORDER BY written_at DESC LIMIT ?"
        rows = self.repo.db.fetchall(query, (signal_type, limit))
        return [_row_to_dict(r) for r in rows]

    def find_since(self, ts_iso: str, limit: int = 100) -> list[dict]:
        """Find records since timestamp."""
        query = f"SELECT * FROM {self.table} WHERE written_at >= ? ORDER BY written_at ASC LIMIT ?"
        rows = self.repo.db.fetchall(query, (ts_iso, limit))
        return [_row_to_dict(r) for r in rows]

    def find_recent(self, limit: int = 100) -> list[dict]:
        """Find N most recent records."""
        query = f"SELECT * FROM {self.table} ORDER BY written_at DESC LIMIT ?"
        rows = self.repo.db.fetchall(query, (limit,))
        return [_row_to_dict(r) for r in rows]
