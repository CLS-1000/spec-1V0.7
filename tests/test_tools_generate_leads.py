# @domain:   spec-1
# @module:   test_tools_generate_leads
# @loc:      gh_main
# @status:   testing
# @depends:  NONE

"""Tests for spec1_core.tools.generate_leads CLI."""

from __future__ import annotations

import json
from pathlib import Path

from spec1_core.tools.generate_leads import main


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def test_returns_zero_when_intel_missing(tmp_path):
    rc = main(["--intel", str(tmp_path / "nope.jsonl"), "--out", str(tmp_path / "leads.jsonl")])
    assert rc == 0


def test_writes_leads_for_qualifying_records(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out = tmp_path / "leads.jsonl"
    _write_jsonl(intel, [
        {"record_id": "r1", "content": "nuclear missile launch detected near border", "confidence": 0.9},
        {"record_id": "r2", "content": "routine military exercise announcement", "confidence": 0.6},
    ])
    rc = main(["--intel", str(intel), "--out", str(out)])
    assert rc == 0
    written = _read_jsonl(out)
    assert len(written) >= 1
    assert any("priority" in w for w in written)


def test_min_confidence_filters_records(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out = tmp_path / "leads.jsonl"
    _write_jsonl(intel, [
        {"record_id": "r1", "content": "nuclear strike", "confidence": 0.9},
        {"record_id": "r2", "content": "routine assessment", "confidence": 0.1},  # below threshold
    ])
    rc = main([
        "--intel", str(intel),
        "--out", str(out),
        "--min-confidence", "0.5",
    ])
    assert rc == 0
    written = _read_jsonl(out)
    assert len(written) == 1
    assert written[0]["source_record_ids"] == ["r1"]


def test_max_leads_caps_output(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out = tmp_path / "leads.jsonl"
    _write_jsonl(intel, [
        {"record_id": f"r{i}", "content": "nuclear missile launch detected", "confidence": 0.9}
        for i in range(10)
    ])
    rc = main(["--intel", str(intel), "--out", str(out), "--max-leads", "3"])
    assert rc == 0
    assert len(_read_jsonl(out)) == 3


def test_priority_filter(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out = tmp_path / "leads.jsonl"
    _write_jsonl(intel, [
        {"record_id": "rc", "content": "nuclear missile launch", "confidence": 0.9},  # CRITICAL
        {"record_id": "rh", "content": "sanctions imposed on regime", "confidence": 0.8},  # HIGH
    ])
    rc = main(["--intel", str(intel), "--out", str(out), "--priority", "CRITICAL"])
    assert rc == 0
    written = _read_jsonl(out)
    assert all(w["priority"] == "CRITICAL" for w in written)
