"""Tests for the Legislative & Judicial Desk — schemas, adapters, producer, store, API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cls_osint.schemas import JudicialRecord, StateLegRecord


# ── Helpers ───────────────────────────────────────────────────────────────────

def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _make_judicial(**kwargs) -> JudicialRecord:
    defaults = dict(
        record_id="judicial_abc123",
        judge="Hon. Jane Doe",
        court="9th Circuit",
        district="CA",
        action_type="recusal",
        case_ref="No. 24-9999",
        ruling_summary="Recusal filed in securities case.",
        disclosed_ties=["Former partner at defendant firm"],
        recusal_basis="Prior employment relationship",
        gift_amount=0.0,
        engagement_sponsor="",
        filed_at=_today(),
        source_url="https://uscourts.gov/example",
        metadata={},
    )
    defaults.update(kwargs)
    return JudicialRecord(**defaults)


def _make_state_leg(**kwargs) -> StateLegRecord:
    defaults = dict(
        record_id="stateleg_abc123",
        state="CA",
        bill_id="CA SB 100",
        title="Test Transparency Act",
        sponsor="Sen. A. Example",
        chamber="SENATE",
        status="INTRODUCED",
        summary="Requires real-time disclosure.",
        disclosure_regime="FULL",
        disclosure_gap=False,
        filed_at=_today(),
        source_url="https://leginfo.legislature.ca.gov/example",
        tags=["transparency"],
        metadata={},
    )
    defaults.update(kwargs)
    return StateLegRecord(**defaults)


# ── JudicialRecord schema ─────────────────────────────────────────────────────

class TestJudicialRecord:
    def test_make_id_is_deterministic(self):
        rid1 = JudicialRecord.make_id("Judge A", "recusal", "2024-01-01")
        rid2 = JudicialRecord.make_id("Judge A", "recusal", "2024-01-01")
        assert rid1 == rid2
        assert rid1.startswith("judicial_")

    def test_make_id_differs_for_different_inputs(self):
        rid1 = JudicialRecord.make_id("Judge A", "recusal", "2024-01-01")
        rid2 = JudicialRecord.make_id("Judge B", "ruling", "2024-01-02")
        assert rid1 != rid2

    def test_to_dict_round_trip(self):
        rec = _make_judicial()
        d = rec.to_dict()
        assert d["judge"] == "Hon. Jane Doe"
        assert d["action_type"] == "recusal"
        assert d["disclosed_ties"] == ["Former partner at defendant firm"]
        assert d["gift_amount"] == 0.0
        assert "record_id" in d

    def test_to_osint_record_source_type(self):
        rec = _make_judicial()
        osint = rec.to_osint_record()
        assert osint.source_type == "JUDICIAL"
        assert "recusal" in osint.content.lower()
        assert osint.url == rec.source_url

    def test_to_dict_serialisable(self):
        rec = _make_judicial()
        json.dumps(rec.to_dict())  # must not raise


# ── StateLegRecord schema ─────────────────────────────────────────────────────

class TestStateLegRecord:
    def test_make_id_is_deterministic(self):
        rid1 = StateLegRecord.make_id("CA", "CA SB 100", "2024-01-01")
        rid2 = StateLegRecord.make_id("CA", "CA SB 100", "2024-01-01")
        assert rid1 == rid2
        assert rid1.startswith("state_leg_")

    def test_disclosure_gap_serialises(self):
        rec = _make_state_leg(disclosure_gap=True, disclosure_regime="NONE", state="WY")
        d = rec.to_dict()
        assert d["disclosure_gap"] is True
        assert d["disclosure_regime"] == "NONE"

    def test_to_osint_record_source_type(self):
        rec = _make_state_leg()
        osint = rec.to_osint_record()
        assert osint.source_type == "STATE_LEG"

    def test_to_osint_record_gap_noted_in_content(self):
        rec = _make_state_leg(disclosure_gap=True, state="WY")
        osint = rec.to_osint_record()
        assert "DISCLOSURE GAP" in osint.content

    def test_to_dict_serialisable(self):
        rec = _make_state_leg()
        json.dumps(rec.to_dict())


# ── Judicial adapter ──────────────────────────────────────────────────────────

class TestJudicialAdapter:
    def test_collect_returns_list_on_network_failure(self):
        from cls_osint.adapters import judicial as j_adapter
        with patch("requests.get", side_effect=ConnectionError("offline")):
            records = j_adapter.collect()
        assert isinstance(records, list)
        assert len(records) >= 1
        assert all(isinstance(r, JudicialRecord) for r in records)

    def test_synthetic_sample_has_three_records(self):
        from cls_osint.adapters.judicial import _synthetic_sample
        records = _synthetic_sample()
        assert len(records) == 3
        action_types = {r.action_type for r in records}
        assert "recusal" in action_types

    def test_iter_records_yields_judicial_records(self):
        from cls_osint.adapters import judicial as j_adapter
        with patch("requests.get", side_effect=ConnectionError("offline")):
            records = list(j_adapter.iter_records())
        assert len(records) >= 1

    def test_parse_action_type_classifies_correctly(self):
        from cls_osint.adapters.judicial import _parse_action_type
        assert _parse_action_type("judge recused himself") == "recusal"
        assert _parse_action_type("financial disclosure filed") == "disclosure"
        assert _parse_action_type("gift report submitted") == "gift"
        assert _parse_action_type("speaking engagement at law school") == "speaking_engagement"
        assert _parse_action_type("opinion issued in patent case") == "ruling"


# ── State legislative adapter ─────────────────────────────────────────────────

class TestStateLegAdapter:
    def test_collect_returns_list_on_network_failure(self):
        from cls_osint.adapters import state_legislative as sl_adapter
        with patch("requests.get", side_effect=ConnectionError("offline")):
            records = sl_adapter.collect()
        assert isinstance(records, list)
        assert len(records) >= 1
        assert all(isinstance(r, StateLegRecord) for r in records)

    def test_synthetic_sample_has_three_records(self):
        from cls_osint.adapters.state_legislative import _synthetic_sample
        records = _synthetic_sample()
        assert len(records) == 3

    def test_synthetic_sample_has_disclosure_gap(self):
        from cls_osint.adapters.state_legislative import _synthetic_sample
        records = _synthetic_sample()
        assert any(r.disclosure_gap for r in records)

    def test_get_disclosure_regime_none_state(self):
        from cls_osint.adapters.state_legislative import _get_disclosure_regime
        regime, has_gap = _get_disclosure_regime("WY")
        assert regime == "NONE"
        assert has_gap is True

    def test_get_disclosure_regime_full_state(self):
        from cls_osint.adapters.state_legislative import _get_disclosure_regime
        regime, has_gap = _get_disclosure_regime("CA")
        assert regime == "FULL"
        assert has_gap is False

    def test_classify_status(self):
        from cls_osint.adapters.state_legislative import _classify_status
        assert _classify_status("enacted and signed") == "ENACTED"
        assert _classify_status("passed the senate") == "PASSED_SENATE"
        assert _classify_status("passed the house") == "PASSED_HOUSE"
        assert _classify_status("failed on floor vote") == "FAILED"
        assert _classify_status("introduced in committee") == "INTRODUCED"


# ── LegJudBrief producer ──────────────────────────────────────────────────────

class TestLegJudProducer:
    def test_empty_records_all_no_signal(self):
        from cls_leg_jud.producer import produce_brief
        brief = produce_brief([], run_id="test_run_001")
        assert brief.eligible_records == 0
        for section in brief.sections:
            assert section.body == "NO SIGNAL THIS CYCLE"

    def test_low_confidence_excluded(self):
        from cls_leg_jud.producer import produce_brief
        records = [
            {
                "record_id": "r1",
                "domain": "congress.vote",
                "composite_confidence": 0.30,
                "summary": "Bill introduced.",
                "subject": "Rep. Smith",
                "run_id": "run_001",
                "metadata": {},
            }
        ]
        brief = produce_brief(records, run_id="run_001")
        assert brief.eligible_records == 0

    def test_eligible_record_routes_to_correct_section(self):
        from cls_leg_jud.producer import produce_brief
        records = [
            {
                "record_id": "r1",
                "domain": "congress.vote",
                "composite_confidence": 0.75,
                "summary": "H.R.100 passed committee vote.",
                "subject": "Rep. Jane Smith",
                "run_id": "run_002",
                "metadata": {"chamber": "HOUSE"},
            }
        ]
        brief = produce_brief(records, run_id="run_002")
        assert brief.eligible_records == 1
        fed_section = next(s for s in brief.sections if s.kind == "federal_members")
        assert fed_section.body != "NO SIGNAL THIS CYCLE"

    def test_judicial_domain_routes_to_judicial_section(self):
        from cls_leg_jud.producer import produce_brief
        records = [
            {
                "record_id": "r2",
                "domain": "judicial.recusal",
                "composite_confidence": 0.65,
                "summary": "Judge Chen recused in securities case.",
                "subject": "Hon. Maria Chen",
                "run_id": "run_003",
                "metadata": {"court": "9th Circuit", "action_type": "recusal"},
            }
        ]
        brief = produce_brief(records, run_id="run_003")
        jud_section = next(s for s in brief.sections if s.kind == "judicial")
        assert jud_section.body != "NO SIGNAL THIS CYCLE"
        assert "recusal" in jud_section.body.lower() or "Chen" in jud_section.body

    def test_state_leg_disclosure_gap_appears_in_output(self):
        from cls_leg_jud.producer import produce_brief
        records = [
            {
                "record_id": "r3",
                "domain": "state_leg.bill",
                "composite_confidence": 0.55,
                "summary": "Tax exemption bill enacted.",
                "subject": "WY Legislature",
                "run_id": "run_004",
                "metadata": {
                    "state": "WY",
                    "bill_id": "WY HB 0044",
                    "disclosure_gap": True,
                    "disclosure_regime": "NONE",
                },
            }
        ]
        brief = produce_brief(records, run_id="run_004")
        state_section = next(s for s in brief.sections if s.kind == "state_leg")
        assert "DISCLOSURE GAP" in state_section.body

    def test_prohibited_vocabulary_absent_from_stated_purpose(self):
        from cls_leg_jud.producer import produce_brief
        records = [
            {
                "record_id": "r4",
                "domain": "congress.vote",
                "composite_confidence": 0.80,
                "summary": "H.R.200 reduces capital gains tax.",
                "subject": "Rep. John Adams",
                "run_id": "run_005",
                "metadata": {
                    "sector_tags": ["finance", "tax"],
                    "fara_matches": ["BankLobby LLC"],
                    "committee_overlap": ["Ways and Means"],
                },
            }
        ]
        brief = produce_brief(records, run_id="run_005")
        spvob = next(s for s in brief.sections if s.kind == "stated_purpose_vs_beneficiary")
        body = spvob.body.lower()
        prohibited = ["corrupt", "honest", "partisan", "scheming", "admit", "deny",
                      "alarmingly", "surprisingly", "conveniently"]
        for word in prohibited:
            assert word not in body, f"Prohibited word '{word}' found in stated_purpose output"

    def test_section_kinds_complete(self):
        from cls_leg_jud.producer import produce_brief
        from cls_leg_jud.schemas import SECTION_KINDS
        brief = produce_brief([], run_id="run_006")
        produced_kinds = [s.kind for s in brief.sections]
        for kind in SECTION_KINDS:
            assert kind in produced_kinds


# ── LegJudStore ───────────────────────────────────────────────────────────────

class TestLegJudStore:
    def test_save_and_read_all(self, tmp_path):
        from cls_leg_jud.store import LegJudStore
        from cls_leg_jud.producer import produce_brief
        store = LegJudStore(tmp_path / "leg_jud.jsonl")
        brief = produce_brief([], run_id="store_test_001")
        saved = store.save(brief)
        assert saved["run_id"] == "store_test_001"
        items = list(store.read_all())
        assert len(items) == 1

    def test_latest_returns_most_recent(self, tmp_path):
        from cls_leg_jud.store import LegJudStore
        from cls_leg_jud.producer import produce_brief
        store = LegJudStore(tmp_path / "leg_jud.jsonl")
        store.save(produce_brief([], run_id="r1"))
        store.save(produce_brief([], run_id="r2"))
        latest = store.latest()
        assert latest is not None
        assert latest["run_id"] == "r2"

    def test_count(self, tmp_path):
        from cls_leg_jud.store import LegJudStore
        from cls_leg_jud.producer import produce_brief
        store = LegJudStore(tmp_path / "leg_jud.jsonl")
        assert store.count() == 0
        store.save(produce_brief([], run_id="r1"))
        assert store.count() == 1


# ── LegJudFormatter ───────────────────────────────────────────────────────────

class TestLegJudFormatter:
    def test_to_markdown_termination_on_zero_eligible(self):
        from cls_leg_jud.producer import produce_brief
        from cls_leg_jud.formatter import to_markdown
        brief = produce_brief([], run_id="format_test_001")
        md = to_markdown(brief)
        assert "NO LEGISLATIVE OR JUDICIAL SIGNAL" in md

    def test_section_to_markdown_standalone(self):
        from cls_leg_jud.producer import produce_brief
        from cls_leg_jud.formatter import section_to_markdown
        records = [
            {
                "record_id": "r1",
                "domain": "fara.filing",
                "composite_confidence": 0.70,
                "summary": "Lobby firm filed FARA registration.",
                "subject": "LobbyFirm LLC",
                "run_id": "format_test_002",
                "metadata": {},
            }
        ]
        brief = produce_brief(records, run_id="format_test_002")
        for section in brief.sections:
            section_md = section_to_markdown(section)
            # Each section must start with its own heading — standalone readable
            assert section_md.startswith("## ")
            # Must not reference other sections by title
            other_titles = [
                s.title for s in brief.sections if s.kind != section.kind
            ]
            for title in other_titles:
                assert title not in section_md

    def test_to_json_summary_shape(self):
        from cls_leg_jud.producer import produce_brief
        from cls_leg_jud.formatter import to_json_summary
        brief = produce_brief([], run_id="format_test_003")
        summary = to_json_summary(brief)
        assert "brief_id" in summary
        assert "sections" in summary
        for item in summary["sections"]:
            assert "kind" in item
            assert "has_signal" in item


# ── API routes ────────────────────────────────────────────────────────────────

class TestLegJudAPIRoutes:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        import sys
        from unittest.mock import MagicMock

        monkeypatch.setenv("SPEC1_STORE_PATH", str(tmp_path / "intel.jsonl"))
        monkeypatch.setenv("SPEC1_OSINT_PATH", str(tmp_path / "osint.jsonl"))
        monkeypatch.setenv("SPEC1_LEG_JUD_PATH", str(tmp_path / "leg_jud.jsonl"))
        (tmp_path / "osint.jsonl").write_text("")

        # Stub out modules that can't be installed in this test environment
        for mod in ("feedparser", "sgmllib3k", "bs4", "apscheduler",
                    "apscheduler.schedulers", "apscheduler.schedulers.background"):
            if mod not in sys.modules:
                sys.modules[mod] = MagicMock()

        # Stub spec1_core.app.cycle to avoid its heavy import chain
        mock_cycle = MagicMock()
        mock_cycle.run_cycle.return_value = {"run_id": "test", "records_stored": 0}
        monkeypatch.setitem(sys.modules, "spec1_core.app.cycle", mock_cycle)

        import importlib
        import spec1_api.main as main_mod
        importlib.reload(main_mod)
        from fastapi.testclient import TestClient
        with TestClient(main_mod.app) as c:
            yield c

    def test_leg_jud_brief_returns_200(self, client):
        r = client.get("/api/v1/leg_jud/brief")
        assert r.status_code == 200

    def test_leg_jud_judicial_returns_200(self, client):
        r = client.get("/api/v1/leg_jud/judicial")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data

    def test_leg_jud_state_leg_returns_200(self, client):
        r = client.get("/api/v1/leg_jud/state_leg")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data

    def test_leg_jud_judicial_filter_by_judge(self, tmp_path, monkeypatch):
        import sys
        from unittest.mock import MagicMock
        for mod in ("feedparser", "sgmllib3k", "bs4", "apscheduler",
                    "apscheduler.schedulers", "apscheduler.schedulers.background"):
            if mod not in sys.modules:
                sys.modules[mod] = MagicMock()
        mock_cycle = MagicMock()
        mock_cycle.run_cycle.return_value = {"run_id": "test", "records_stored": 0}
        monkeypatch.setitem(sys.modules, "spec1_core.app.cycle", mock_cycle)

        osint_path = tmp_path / "osint2.jsonl"
        record = {
            "record_id": "j1",
            "source_type": "JUDICIAL",
            "source_name": "federal_courts",
            "content": "Judge Test recusal",
            "url": "https://example.com",
            "collected_at": "2024-01-01T00:00:00+00:00",
            "metadata": {"judge": "Hon. Test Judge", "action_type": "recusal", "court": "SDNY"},
        }
        osint_path.write_text(json.dumps(record) + "\n")
        monkeypatch.setenv("SPEC1_OSINT_PATH", str(osint_path))
        monkeypatch.setenv("SPEC1_LEG_JUD_PATH", str(tmp_path / "lj2.jsonl"))
        monkeypatch.setenv("SPEC1_STORE_PATH", str(tmp_path / "intel2.jsonl"))

        import importlib
        import spec1_api.dependencies as deps_mod
        import spec1_api.main as main_mod
        deps_mod.get_osint_store.cache_clear()
        importlib.reload(main_mod)
        from fastapi.testclient import TestClient
        with TestClient(main_mod.app) as c:
            r = c.get("/api/v1/leg_jud/judicial?judge=test")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
