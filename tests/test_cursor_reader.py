# @domain:   spec-1
# @module:   test_cursor_reader
# @loc:      gh_main
# @status:   testing
# @depends:  NONE

"""Tests for cls_db.cursor_reader — cursor-based JSONL pagination."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cls_db.cursor_reader import Cursor, JSONLCursorReader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _make_records(n: int) -> list[dict]:
    return [
        {
            "record_id": f"rec-{i:04d}",
            "written_at": f"2026-01-{i // 100 + 1:02d}T{i % 24:02d}:00:00+00:00",
            "value": i,
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Cursor tests
# ---------------------------------------------------------------------------


class TestCursor:
    def test_round_trip_serialisation(self):
        c = Cursor(start_ts="2026-05-19T10:00:00+00:00", start_id="rec-0001")
        assert Cursor.from_string(c.to_string()) == c

    def test_to_string_contains_pipe(self):
        c = Cursor(start_ts="2026-01-01T00:00:00+00:00", start_id="abc")
        assert "|" in c.to_string()

    def test_from_string_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid cursor token"):
            Cursor.from_string("no-pipe-here")

    def test_ordering(self):
        early = Cursor(start_ts="2026-01-01T00:00:00+00:00", start_id="a")
        late = Cursor(start_ts="2026-06-01T00:00:00+00:00", start_id="b")
        assert early < late

    def test_id_tiebreak_ordering(self):
        c1 = Cursor(start_ts="2026-01-01T00:00:00+00:00", start_id="a")
        c2 = Cursor(start_ts="2026-01-01T00:00:00+00:00", start_id="b")
        assert c1 < c2


# ---------------------------------------------------------------------------
# JSONLCursorReader tests
# ---------------------------------------------------------------------------


class TestJSONLCursorReaderBasics:
    def test_read_chunk_from_start(self, tmp_path: Path):
        records = _make_records(10)
        path = tmp_path / "data.jsonl"
        _write_jsonl(path, records)

        reader = JSONLCursorReader(path, chunk_size=5)
        chunk, next_cursor = reader.read_chunk()

        assert len(chunk) == 5
        assert next_cursor is not None
        assert chunk[0]["record_id"] == "rec-0000"
        assert chunk[4]["record_id"] == "rec-0004"

    def test_read_chunk_continues_from_cursor(self, tmp_path: Path):
        records = _make_records(10)
        path = tmp_path / "data.jsonl"
        _write_jsonl(path, records)

        reader = JSONLCursorReader(path, chunk_size=5)
        first_chunk, cursor1 = reader.read_chunk()
        assert cursor1 is not None

        second_chunk, cursor2 = reader.read_chunk(cursor=cursor1)
        assert len(second_chunk) == 5
        assert second_chunk[0]["record_id"] == "rec-0005"

    def test_final_page_returns_none_cursor(self, tmp_path: Path):
        records = _make_records(5)
        path = tmp_path / "data.jsonl"
        _write_jsonl(path, records)

        reader = JSONLCursorReader(path, chunk_size=10)
        chunk, next_cursor = reader.read_chunk()

        assert len(chunk) == 5
        assert next_cursor is None

    def test_empty_file_returns_empty_and_none(self, tmp_path: Path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        reader = JSONLCursorReader(path)
        chunk, cursor = reader.read_chunk()
        assert chunk == []
        assert cursor is None

    def test_missing_file_returns_empty(self, tmp_path: Path):
        reader = JSONLCursorReader(tmp_path / "nonexistent.jsonl")
        chunk, cursor = reader.read_chunk()
        assert chunk == []
        assert cursor is None

    def test_invalid_json_lines_skipped(self, tmp_path: Path):
        path = tmp_path / "data.jsonl"
        lines = [
            '{"record_id": "r1", "written_at": "2026-01-01T00:00:00+00:00"}\n',
            "NOT JSON\n",
            '{"record_id": "r2", "written_at": "2026-01-02T00:00:00+00:00"}\n',
        ]
        path.write_text("".join(lines))

        reader = JSONLCursorReader(path, chunk_size=10)
        chunk, _ = reader.read_chunk()
        assert len(chunk) == 2
        assert {r["record_id"] for r in chunk} == {"r1", "r2"}


class TestJSONLCursorReaderIteration:
    def test_read_all_chunked_yields_all_records(self, tmp_path: Path):
        records = _make_records(25)
        path = tmp_path / "data.jsonl"
        _write_jsonl(path, records)

        reader = JSONLCursorReader(path, chunk_size=10)
        collected: list[dict] = []
        for chunk in reader.read_all_chunked():
            collected.extend(chunk)

        assert len(collected) == 25

    def test_read_all_chunked_custom_limit(self, tmp_path: Path):
        records = _make_records(12)
        path = tmp_path / "data.jsonl"
        _write_jsonl(path, records)

        reader = JSONLCursorReader(path)
        chunks = list(reader.read_all_chunked(limit=4))
        assert len(chunks) == 3  # 4 + 4 + 4

    def test_iter_records_yields_every_record(self, tmp_path: Path):
        records = _make_records(20)
        path = tmp_path / "data.jsonl"
        _write_jsonl(path, records)

        reader = JSONLCursorReader(path)
        all_records = list(reader.iter_records())
        assert len(all_records) == 20

    def test_count(self, tmp_path: Path):
        records = _make_records(7)
        path = tmp_path / "data.jsonl"
        _write_jsonl(path, records)

        reader = JSONLCursorReader(path)
        assert reader.count() == 7

    def test_custom_id_and_ts_fields(self, tmp_path: Path):
        """Cursor uses custom field names correctly."""
        records = [
            {"id": f"id-{i}", "ts": f"2026-{i:02d}-01T00:00:00+00:00", "val": i}
            for i in range(1, 6)
        ]
        path = tmp_path / "custom.jsonl"
        _write_jsonl(path, records)

        reader = JSONLCursorReader(path, chunk_size=3, ts_field="ts", id_field="id")
        chunk1, cursor = reader.read_chunk()
        assert len(chunk1) == 3
        assert cursor is not None
        assert cursor.start_id == "id-3"

        chunk2, cursor2 = reader.read_chunk(cursor=cursor)
        assert len(chunk2) == 2
        assert cursor2 is None
