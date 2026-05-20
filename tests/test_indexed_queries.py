"""Indexed query layer tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from cls_db.database import Database
from cls_db.repository import Repository
from cls_db.indexed_queries import IndexedQueryLayer


@pytest.fixture
def indexed_repo(tmp_path: Path) -> IndexedQueryLayer:
    db = Database(tmp_path / "test.db")
    db.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT UNIQUE,
            source_type TEXT,
            status TEXT,
            signal_type TEXT,
            written_at TEXT
        )
    """)
    repo = Repository(db, "signals", "record_id")
    repo.insert({"record_id": "s1", "source_type": "RSS",  "status": "ACTIVE",   "signal_type": "THREAT", "written_at": "2026-05-01T00:00:00+00:00"})
    repo.insert({"record_id": "s2", "source_type": "FARA", "status": "INACTIVE", "signal_type": "FARA",   "written_at": "2026-05-02T00:00:00+00:00"})
    repo.insert({"record_id": "s3", "source_type": "RSS",  "status": "ACTIVE",   "signal_type": "PSYOP",  "written_at": "2026-05-03T00:00:00+00:00"})
    return IndexedQueryLayer(repo)


def test_find_by_source(indexed_repo: IndexedQueryLayer):
    results = indexed_repo.find_by_source("RSS", limit=10)
    assert len(results) == 2
    assert all(r["source_type"] == "RSS" for r in results)


def test_find_by_source_no_match(indexed_repo: IndexedQueryLayer):
    results = indexed_repo.find_by_source("CONGRESSIONAL", limit=10)
    assert results == []


def test_find_by_status(indexed_repo: IndexedQueryLayer):
    results = indexed_repo.find_by_status("ACTIVE", limit=10)
    assert len(results) == 2
    assert all(r["status"] == "ACTIVE" for r in results)


def test_find_by_signal_type(indexed_repo: IndexedQueryLayer):
    results = indexed_repo.find_by_signal_type("THREAT", limit=10)
    assert len(results) == 1
    assert results[0]["record_id"] == "s1"


def test_find_since(indexed_repo: IndexedQueryLayer):
    results = indexed_repo.find_since("2026-05-02T00:00:00+00:00", limit=10)
    assert len(results) == 2
    assert results[0]["record_id"] == "s2"


def test_find_recent(indexed_repo: IndexedQueryLayer):
    results = indexed_repo.find_recent(limit=2)
    assert len(results) == 2
    assert results[0]["record_id"] == "s3"


def test_find_recent_limit(indexed_repo: IndexedQueryLayer):
    results = indexed_repo.find_recent(limit=1)
    assert len(results) == 1
