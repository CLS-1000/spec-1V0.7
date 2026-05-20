"""Tests for spec1_core.schemas.brief — WorldStateBrief value objects."""

from __future__ import annotations

import pytest

from spec1_core.schemas.brief import BriefSection, WorldStateBrief


class TestBriefSection:
    def test_frozen(self):
        section = BriefSection(kind="congress_trade", valid=True, payload={"x": 1})
        with pytest.raises((AttributeError, TypeError)):
            section.valid = False  # type: ignore[misc]

    def test_valid_true(self):
        section = BriefSection(kind="fara_proximity", valid=True, payload={})
        assert section.valid is True

    def test_valid_false(self):
        section = BriefSection(kind="sector_signal", valid=False, payload={})
        assert section.valid is False

    def test_payload_is_preserved(self):
        payload = {"member": "Smith", "ticker": "LMT"}
        section = BriefSection(kind="congress_trade", valid=True, payload=payload)
        assert section.payload["member"] == "Smith"
        assert section.payload["ticker"] == "LMT"

    def test_all_section_kinds_accepted(self):
        for kind in ("congress_trade", "fara_proximity", "model_legislation", "sector_signal"):
            section = BriefSection(kind=kind, valid=True, payload={})
            assert section.kind == kind


class TestWorldStateBrief:
    def _make_section(self, kind="congress_trade", valid=True):
        return BriefSection(kind=kind, valid=valid, payload={})

    def test_frozen(self):
        brief = WorldStateBrief(synopsis="Today's brief", sections=())
        with pytest.raises((AttributeError, TypeError)):
            brief.synopsis = "changed"  # type: ignore[misc]

    def test_synopsis_stored(self):
        brief = WorldStateBrief(synopsis="State of the world", sections=())
        assert brief.synopsis == "State of the world"

    def test_sections_empty_tuple(self):
        brief = WorldStateBrief(synopsis="synopsis", sections=())
        assert brief.sections == ()

    def test_sections_stored_as_tuple(self):
        s1 = self._make_section("congress_trade")
        s2 = self._make_section("fara_proximity")
        brief = WorldStateBrief(synopsis="synopsis", sections=(s1, s2))
        assert len(brief.sections) == 2
        assert brief.sections[0] is s1
        assert brief.sections[1] is s2

    def test_valid_sections_filter(self):
        valid = self._make_section("congress_trade", valid=True)
        invalid = self._make_section("sector_signal", valid=False)
        brief = WorldStateBrief(synopsis="synopsis", sections=(valid, invalid))
        valid_sections = [s for s in brief.sections if s.valid]
        assert len(valid_sections) == 1
        assert valid_sections[0].kind == "congress_trade"

    def test_equality(self):
        s = BriefSection(kind="fara_proximity", valid=True, payload={"score": 0.9})
        b1 = WorldStateBrief(synopsis="same", sections=(s,))
        b2 = WorldStateBrief(synopsis="same", sections=(s,))
        assert b1 == b2

    def test_inequality_on_synopsis(self):
        b1 = WorldStateBrief(synopsis="A", sections=())
        b2 = WorldStateBrief(synopsis="B", sections=())
        assert b1 != b2
