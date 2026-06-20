# @domain:   spec-1
# @module:   test_indexed_queries
# @loc:      gh_main
# @status:   testing
# @depends:  NONE

"""Tests for cls_db.indexed_queries — IndexedQueryLayer."""

from __future__ import annotations

import pytest

from cls_db.database import Database
from cls_db.migrate import ensure_schema
from cls_db.repository import Repository
from cls_db.indexed_queries import IndexedQueryLayer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def leads_repo(tmp_path):
    db = Database(tmp_path / "test.db")
    ensure_schema(db)
    return Repository(db, "leads", pk_field="lead_id")


@pytest.fixture
def leads_query(leads_repo):
    return IndexedQueryLayer(leads_repo, default_limit=10)


def _insert_leads(repo: Repository, n: int) -> None:
    for i in range(n):
        priority = "HIGH" if i % 2 == 0 else "LOW"
        repo.insert(
            {
                "lead_id": f"l{i:04d}",
                "title": f"Lead {i}",
                "priority": priority,
                "category": "CYBER",
            }
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestIndexedQueryLayerBasics:
    def test_count_empty_table(self, leads_query):
        assert leads_query.count() == 0

    def test_count_after_inserts(self, leads_repo, leads_query):
        _insert_leads(leads_repo, 5)
        assert leads_query.count() == 5

    def test_latest_returns_n_records(self, leads_repo, leads_query):
        _insert_leads(leads_repo, 10)
        results = leads_query.latest(3)
        assert len(results) == 3

    def test_latest_default_limit(self, leads_repo, leads_query):
        _insert_leads(leads_repo, 15)
        results = leads_query.latest()
        assert len(results) == 10  # default_limit

    def test_by_field_single_match(self, leads_repo, leads_query):
        leads_repo.insert({"lead_id": "l-target", "title": "Target", "priority": "CRITICAL"})
        _insert_leads(leads_repo, 4)

        results = leads_query.by_field("priority", "CRITICAL")
        assert len(results) == 1
        assert results[0]["lead_id"] == "l-target"

    def test_by_field_multiple_matches(self, leads_repo, leads_query):
        _insert_leads(leads_repo, 6)  # 3 HIGH, 3 LOW
        high = leads_query.by_field("priority", "HIGH")
        assert len(high) == 3

    def test_by_field_no_match(self, leads_repo, leads_query):
        _insert_leads(leads_repo, 4)
        results = leads_query.by_field("priority", "NONEXISTENT")
        assert results == []

    def test_page_basic(self, leads_repo, leads_query):
        _insert_leads(leads_repo, 10)
        page = leads_query.page(limit=5, offset=0)
        assert len(page) == 5
        assert page[0]["lead_id"] == "l0000"

    def test_page_offset(self, leads_repo, leads_query):
        _insert_leads(leads_repo, 10)
        page1 = leads_query.page(limit=5, offset=0)
        page2 = leads_query.page(limit=5, offset=5)
        ids1 = {r["lead_id"] for r in page1}
        ids2 = {r["lead_id"] for r in page2}
        assert ids1.isdisjoint(ids2)

    def test_page_beyond_end(self, leads_repo, leads_query):
        _insert_leads(leads_repo, 3)
        page = leads_query.page(limit=10, offset=10)
        assert page == []

    def test_get_existing(self, leads_repo, leads_query):
        leads_repo.insert({"lead_id": "l-get", "title": "Get me"})
        result = leads_query.get("l-get")
        assert result is not None
        assert result["lead_id"] == "l-get"

    def test_get_missing_returns_none(self, leads_query):
        assert leads_query.get("nonexistent") is None


class TestIndexedQueryLayerByFields:
    def test_by_fields_single_filter(self, leads_repo, leads_query):
        _insert_leads(leads_repo, 6)
        results = leads_query.by_fields({"priority": "HIGH"})
        assert all(r["priority"] == "HIGH" for r in results)

    def test_by_fields_multi_filter(self, leads_repo, leads_query):
        leads_repo.insert({"lead_id": "l-match", "priority": "HIGH", "category": "CYBER", "title": "A"})
        leads_repo.insert({"lead_id": "l-nomatch", "priority": "HIGH", "category": "MILITARY", "title": "B"})

        results = leads_query.by_fields({"priority": "HIGH", "category": "CYBER"})
        assert len(results) == 1
        assert results[0]["lead_id"] == "l-match"

    def test_by_fields_empty_filters_returns_page(self, leads_repo, leads_query):
        _insert_leads(leads_repo, 5)
        results = leads_query.by_fields({})
        assert len(results) == 5

    def test_by_fields_limit_respected(self, leads_repo, leads_query):
        _insert_leads(leads_repo, 20)
        results = leads_query.by_fields({"priority": "HIGH"}, limit=2)
        assert len(results) == 2


class TestDualWriterIntegration:
    def test_dual_writer_indexed_queries(self, tmp_path):
        from cls_db.dual_write import make_dual_writer

        writer = make_dual_writer(
            jsonl_path=tmp_path / "leads.jsonl",
            db_path=tmp_path / "spec1.db",
            table="leads",
            pk_field="lead_id",
        )
        for i in range(5):
            writer.write({"lead_id": f"l{i}", "title": f"Lead {i}", "priority": "HIGH"})

        q = writer.indexed_queries()
        assert q.count() == 5
        results = q.by_field("priority", "HIGH")
        assert len(results) == 5

    def test_dual_writer_read_chunked(self, tmp_path):
        from cls_db.dual_write import make_dual_writer

        writer = make_dual_writer(
            jsonl_path=tmp_path / "data.jsonl",
            db_path=tmp_path / "spec1.db",
            table="leads",
            pk_field="lead_id",
        )
        for i in range(25):
            writer.write({"lead_id": f"l{i:04d}", "title": f"Lead {i}"})

        all_records: list[dict] = []
        for chunk in writer.read_chunked(limit=10):
            all_records.extend(chunk)

        assert len(all_records) == 25
