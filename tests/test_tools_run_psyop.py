"""Tests for spec1_engine.tools.run_psyop CLI."""

from __future__ import annotations

import json
from pathlib import Path

from spec1_engine.tools.run_psyop import main


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


def test_main_returns_zero_when_intel_missing(tmp_path):
    rc = main(["--intel", str(tmp_path / "nope.jsonl"), "--out", str(tmp_path / "out.jsonl")])
    assert rc == 0
    assert not (tmp_path / "out.jsonl").exists()


def test_main_returns_zero_when_intel_empty(tmp_path):
    intel = tmp_path / "intel.jsonl"
    intel.write_text("", encoding="utf-8")
    rc = main(["--intel", str(intel), "--out", str(tmp_path / "out.jsonl")])
    assert rc == 0


def test_main_writes_one_score_per_record(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out = tmp_path / "psyop.jsonl"
    _write_jsonl(intel, [
        {"record_id": "r1", "content": "election interference detected in social media campaign"},
        {"record_id": "r2", "content": "routine quarterly economic report on agriculture sector"},
    ])

    rc = main(["--intel", str(intel), "--out", str(out)])
    assert rc == 0
    written = _read_jsonl(out)
    assert len(written) == 2
    assert all("classification" in entry for entry in written)
    assert all("written_at" in entry for entry in written)


def test_main_skips_records_without_text(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out = tmp_path / "psyop.jsonl"
    _write_jsonl(intel, [
        {"record_id": "r1", "content": "election interference"},
        {"record_id": "r2"},  # no text — skipped by score_records
    ])
    rc = main(["--intel", str(intel), "--out", str(out)])
    assert rc == 0
    written = _read_jsonl(out)
    assert len(written) == 1
    assert written[0]["metadata"]["source_record_id"] == "r1"


def test_main_min_classification_filters(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out = tmp_path / "psyop.jsonl"
    # Mix of clean text and text that hits multiple psyop indicators
    _write_jsonl(intel, [
        {"record_id": "r_clean", "content": "weather forecast for monday"},
        {"record_id": "r_risky",
         "content": "false flag crisis actor staged government orchestrated inside job"},
    ])
    rc = main([
        "--intel", str(intel),
        "--out", str(out),
        "--min-classification", "MEDIUM_RISK",
    ])
    assert rc == 0
    if not out.exists():
        # Filter removed all scores — acceptable, but our risky text should have survived
        raise AssertionError("expected risky record to survive MEDIUM_RISK filter")
    written = _read_jsonl(out)
    assert written, "filter should have kept at least the risky record"
    assert all(w["classification"] in ("MEDIUM_RISK", "HIGH_RISK") for w in written)


def test_main_appends_to_existing_store(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out = tmp_path / "psyop.jsonl"
    out.write_text(json.dumps({"prior": "entry"}) + "\n", encoding="utf-8")
    _write_jsonl(intel, [{"record_id": "r1", "content": "election interference"}])
    rc = main(["--intel", str(intel), "--out", str(out)])
    assert rc == 0
    written = _read_jsonl(out)
    assert len(written) == 2
    assert written[0] == {"prior": "entry"}
