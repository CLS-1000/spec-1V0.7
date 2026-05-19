"""Tests for spec1_core.app.publishers.x — XPublisher and helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spec1_core.app.publishers.x import (
    MAX_POST_CHARS,
    PublishResult,
    XPublisher,
    _render_section,
    _truncate,
)
from spec1_core.schemas.brief import BriefSection, WorldStateBrief


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _section(kind="congress_trade", valid=True, **payload_kwargs):
    defaults = {
        "congress_trade": {
            "member": "J. Smith", "chamber": "House", "party": "D", "state": "CA",
            "ticker": "LMT", "action": "Buy", "amount_band": "$50k-100k",
            "committee_overlap": 0.82, "donor_proximity": 0.61, "composite": 0.74,
        },
        "fara_proximity": {
            "registrant": "Acme LLC", "country": "Ruritania",
            "bill_id": "HR 1234", "score": 0.91,
        },
        "model_legislation": {
            "origin_state": "TX", "bill_id": "HB 42",
            "n_states": 7, "top_match_pct": 0.87,
        },
        "sector_signal": {
            "sector": "Defense", "active_bills": 14, "velocity": "high",
        },
    }
    payload = {**defaults.get(kind, {}), **payload_kwargs}
    return BriefSection(kind=kind, valid=valid, payload=payload)


def _brief(*sections, synopsis="State of the world"):
    return WorldStateBrief(synopsis=synopsis, sections=tuple(sections))


def _mock_client(tweet_id="tweet-001"):
    client = MagicMock()
    client.create_tweet.return_value = MagicMock(data={"id": tweet_id})
    return client


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------

class TestTruncate:
    def test_short_text_unchanged(self):
        text = "Hello world"
        assert _truncate(text) == text

    def test_exactly_max_chars_unchanged(self):
        text = "a" * MAX_POST_CHARS
        assert _truncate(text) == text

    def test_over_limit_truncated(self):
        text = "a" * (MAX_POST_CHARS + 10)
        result = _truncate(text)
        assert len(result) <= MAX_POST_CHARS
        assert result.endswith("…")

    def test_truncated_length_is_max(self):
        text = "x" * 500
        result = _truncate(text)
        assert len(result) == MAX_POST_CHARS


# ---------------------------------------------------------------------------
# _render_section
# ---------------------------------------------------------------------------

class TestRenderSection:
    def test_congress_trade_format(self):
        s = _section("congress_trade")
        out = _render_section(s, 1, 3)
        assert "[1/3]" in out
        assert "CONGRESS · TRADE CONFLICT" in out
        assert "J. Smith" in out
        assert "LMT" in out
        assert "0.74" in out

    def test_fara_proximity_format(self):
        s = _section("fara_proximity")
        out = _render_section(s, 2, 3)
        assert "[2/3]" in out
        assert "FARA · PROXIMITY FLAG" in out
        assert "Ruritania" in out
        assert "0.91" in out

    def test_model_legislation_format(self):
        s = _section("model_legislation")
        out = _render_section(s, 1, 2)
        assert "MODEL LEGISLATION" in out
        assert "TX" in out
        assert "7 states" in out
        assert "87%" in out

    def test_sector_signal_format(self):
        s = _section("sector_signal")
        out = _render_section(s, 1, 1)
        assert "SECTOR SIGNAL" in out
        assert "Defense" in out
        assert "14" in out

    def test_unknown_kind_raises(self):
        s = BriefSection(kind="congress_trade", valid=True, payload={})
        # monkeypatch kind to something invalid
        object.__setattr__(s, "__class__", BriefSection)
        bad = BriefSection.__new__(BriefSection)
        object.__setattr__(bad, "kind", "unknown_kind")
        object.__setattr__(bad, "valid", True)
        object.__setattr__(bad, "payload", {})
        with pytest.raises(ValueError, match="unknown section kind"):
            _render_section(bad, 1, 1)


# ---------------------------------------------------------------------------
# XPublisher — dry_run
# ---------------------------------------------------------------------------

class TestXPublisherDryRun:
    def _publisher(self):
        return XPublisher(client=MagicMock(), dry_run=True)

    def test_dry_run_returns_result(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(tmp_path / "pub.jsonl"))
        pub = self._publisher()
        brief = _brief(_section("congress_trade"), _section("fara_proximity"))
        result = pub.publish_brief(brief, run_id="run-dry-001")
        assert isinstance(result, PublishResult)
        assert result.run_id == "run-dry-001"
        assert result.thread_root_id == "dry-run"

    def test_dry_run_post_count_includes_header_and_footer(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(tmp_path / "pub.jsonl"))
        pub = self._publisher()
        brief = _brief(_section("congress_trade"), _section("fara_proximity"))
        result = pub.publish_brief(brief, run_id="run-dry-002")
        # 1 header + 2 valid sections + 1 footer = 4
        assert result.posted_count == 4

    def test_dry_run_skips_invalid_sections(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(tmp_path / "pub.jsonl"))
        pub = self._publisher()
        valid = _section("congress_trade", valid=True)
        invalid = _section("sector_signal", valid=False)
        brief = _brief(valid, invalid)
        result = pub.publish_brief(brief, run_id="run-dry-003")
        assert "sector_signal" in result.skipped_sections
        # 1 header + 1 valid section + 1 footer = 3
        assert result.posted_count == 3

    def test_dry_run_appends_event_log(self, tmp_path, monkeypatch):
        log_path = tmp_path / "pub.jsonl"
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(log_path))
        pub = self._publisher()
        brief = _brief(_section("congress_trade"))
        pub.publish_brief(brief, run_id="run-dry-004")
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["event"] == "x_publish"
        assert rec["run_id"] == "run-dry-004"

    def test_no_valid_sections_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(tmp_path / "pub.jsonl"))
        pub = self._publisher()
        brief = _brief(_section("congress_trade", valid=False))
        with pytest.raises(RuntimeError, match="no valid sections"):
            pub.publish_brief(brief, run_id="run-dry-005")


# ---------------------------------------------------------------------------
# XPublisher — idempotency
# ---------------------------------------------------------------------------

class TestXPublisherIdempotency:
    def test_second_publish_is_skipped(self, tmp_path, monkeypatch):
        log_path = tmp_path / "pub.jsonl"
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(log_path))
        pub = XPublisher(client=MagicMock(), dry_run=True)
        brief = _brief(_section("fara_proximity"))
        r1 = pub.publish_brief(brief, run_id="run-idem-001")
        r2 = pub.publish_brief(brief, run_id="run-idem-001")
        assert r1.run_id == r2.run_id
        # Only one line appended to the log
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_different_run_ids_both_published(self, tmp_path, monkeypatch):
        log_path = tmp_path / "pub.jsonl"
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(log_path))
        pub = XPublisher(client=MagicMock(), dry_run=True)
        brief = _brief(_section("sector_signal"))
        pub.publish_brief(brief, run_id="run-A")
        pub.publish_brief(brief, run_id="run-B")
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# XPublisher — live emit (mocked tweepy)
# ---------------------------------------------------------------------------

class TestXPublisherLiveEmit:
    def test_live_emit_calls_create_tweet(self, tmp_path, monkeypatch):
        log_path = tmp_path / "pub.jsonl"
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(log_path))
        client = _mock_client("tw-999")
        pub = XPublisher(client=client, dry_run=False)
        brief = _brief(_section("congress_trade"))
        result = pub.publish_brief(brief, run_id="run-live-001")
        assert client.create_tweet.call_count >= 2  # at least header + footer
        assert result.thread_root_id == "tw-999"

    def test_live_emit_chains_replies(self, tmp_path, monkeypatch):
        log_path = tmp_path / "pub.jsonl"
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(log_path))
        call_count = 0
        def fake_tweet(text, in_reply_to_tweet_id=None):
            nonlocal call_count
            call_count += 1
            return MagicMock(data={"id": f"tw-{call_count}"})
        client = MagicMock()
        client.create_tweet.side_effect = fake_tweet
        pub = XPublisher(client=client, dry_run=False)
        brief = _brief(_section("congress_trade"), _section("fara_proximity"))
        pub.publish_brief(brief, run_id="run-live-002")
        # Calls: header, section1, section2, footer = 4
        assert client.create_tweet.call_count == 4
        # Second call should reply to first tweet
        _, kwargs = client.create_tweet.call_args_list[1]
        assert kwargs["in_reply_to_tweet_id"] == "tw-1"


# ---------------------------------------------------------------------------
# _render_thread internals
# ---------------------------------------------------------------------------

class TestRenderThread:
    def _pub(self):
        return XPublisher(client=MagicMock(), dry_run=True)

    def test_header_contains_synopsis(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(tmp_path / "p.jsonl"))
        pub = self._pub()
        brief = _brief(_section("sector_signal"), synopsis="Markets on edge")
        cycle_utc = datetime(2026, 5, 3, 13, 0, 0, tzinfo=timezone.utc)
        posts = pub._render_thread(brief, run_id="x", cycle_utc=cycle_utc)
        assert "Markets on edge" in posts[0]

    def test_footer_contains_run_id_prefix(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(tmp_path / "p.jsonl"))
        pub = self._pub()
        brief = _brief(_section("model_legislation"))
        cycle_utc = datetime(2026, 5, 3, 13, 0, 0, tzinfo=timezone.utc)
        posts = pub._render_thread(brief, run_id="abcdef12345", cycle_utc=cycle_utc)
        assert "abcdef12" in posts[-1]

    def test_each_post_within_char_limit(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPEC1_PUBLISH_LOG", str(tmp_path / "p.jsonl"))
        pub = self._pub()
        sections = [_section(k) for k in ("congress_trade", "fara_proximity",
                                           "model_legislation", "sector_signal")]
        brief = _brief(*sections, synopsis="A" * 200)
        cycle_utc = datetime(2026, 5, 3, 13, 0, 0, tzinfo=timezone.utc)
        posts = pub._render_thread(brief, run_id="run-len", cycle_utc=cycle_utc)
        for post in posts:
            assert len(post) <= MAX_POST_CHARS, f"Post too long ({len(post)}): {post!r}"
