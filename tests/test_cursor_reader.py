"""Cursor pagination tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cls_db.cursor_reader import Cursor, JSONLCursorReader


@pytest.fixture
def sample_jsonl(tmp_path: Path) -> Path:
    path = tmp_path / "test.jsonl"
    records = [
        {"written_at": "2026-05-19T10:00:00+00:00", "record_id": "r1", "data": "a"},
        {"written_at": "2026-05-19T10:01:00+00:00", "record_id": "r2", "data": "b"},
        {"written_at": "2026-05-19T10:02:00+00:00", "record_id": "r3", "data": "c"},
    ]
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


def test_cursor_serialization():
    cursor = Cursor(start_ts="2026-05-19T10:00:00+00:00", start_id="r1")
    s = cursor.to_string()
    cursor2 = Cursor.from_string(s)
    assert cursor2.start_ts == cursor.start_ts
    assert cursor2.start_id == cursor.start_id


def test_read_chunk_from_start(sample_jsonl: Path):
    reader = JSONLCursorReader(sample_jsonl)
    records, next_cursor = reader.read_chunk(cursor=None, limit=2)
    assert len(records) == 2
    assert records[0]["record_id"] == "r1"
    assert next_cursor is not None


def test_read_chunk_from_start_no_limit(sample_jsonl: Path):
    reader = JSONLCursorReader(sample_jsonl)
    records, next_cursor = reader.read_chunk(cursor=None, limit=100)
    assert len(records) == 3
    assert next_cursor is None


def test_read_chunk_with_cursor(sample_jsonl: Path):
    reader = JSONLCursorReader(sample_jsonl)
    cursor = Cursor(start_ts="2026-05-19T10:01:00+00:00", start_id="r2")
    records, next_cursor = reader.read_chunk(cursor=cursor, limit=10)
    assert len(records) == 2
    assert records[0]["record_id"] == "r2"


def test_read_all_chunked(sample_jsonl: Path):
    reader = JSONLCursorReader(sample_jsonl)
    chunks = list(reader.read_all_chunked(limit=1))
    assert len(chunks) == 3
    assert chunks[0][0]["record_id"] == "r1"
    assert chunks[2][0]["record_id"] == "r3"


def test_read_chunk_missing_file(tmp_path: Path):
    reader = JSONLCursorReader(tmp_path / "nonexistent.jsonl")
    records, cursor = reader.read_chunk()
    assert records == []
    assert cursor is None


def test_read_chunk_skips_malformed_lines(tmp_path: Path):
    path = tmp_path / "bad.jsonl"
    path.write_text(
        '{"written_at":"2026-01-01T00:00:00+00:00","record_id":"r1"}\n'
        "not json\n"
        '{"written_at":"2026-01-01T00:00:01+00:00","record_id":"r2"}\n'
    )
    reader = JSONLCursorReader(path)
    records, _ = reader.read_chunk(limit=10)
    assert [r["record_id"] for r in records] == ["r1", "r2"]
