"""Tests for spec1_core.tools.generate_brief CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from spec1_core.tools.generate_brief import main


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def test_rule_based_fallback_writes_brief(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out_dir = tmp_path / "briefs"
    _write_jsonl(intel, [
        {"record_id": "r1", "content": "China expands naval exercises in Taiwan Strait",
         "run_id": "run-001", "written_at": "2026-05-01T12:00:00+00:00"},
        {"record_id": "r2", "content": "Russia escalates cyber operations",
         "run_id": "run-001", "written_at": "2026-05-01T12:00:00+00:00"},
    ])
    rc = main([
        "--intel", str(intel),
        "--run-id", "run-001",
        "--out-dir", str(out_dir),
        "--rule-based",
    ])
    assert rc == 0
    assert (out_dir / "spec1_brief_2026-05-01.md").exists()
    assert (out_dir / "spec1_brief_latest.md").exists()
    assert (out_dir / "brief_index.jsonl").exists()
    index_lines = [
        json.loads(line)
        for line in (out_dir / "brief_index.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert index_lines[0]["run_id"] == "run-001"
    assert index_lines[0]["date"] == "2026-05-01"


def test_latest_picks_most_recent_run(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out_dir = tmp_path / "briefs"
    _write_jsonl(intel, [
        {"record_id": "r1", "content": "old event",
         "run_id": "old", "written_at": "2026-01-01T00:00:00+00:00"},
        {"record_id": "r2", "content": "new event",
         "run_id": "new", "written_at": "2026-05-09T00:00:00+00:00"},
    ])
    rc = main([
        "--intel", str(intel),
        "--run-id", "latest",
        "--out-dir", str(out_dir),
        "--rule-based",
    ])
    assert rc == 0
    index = json.loads((out_dir / "brief_index.jsonl").read_text().strip())
    assert index["run_id"] == "new"


def test_unknown_run_id_raises(tmp_path):
    intel = tmp_path / "intel.jsonl"
    _write_jsonl(intel, [
        {"record_id": "r1", "content": "x", "run_id": "real",
         "written_at": "2026-05-01T00:00:00+00:00"},
    ])
    try:
        main([
            "--intel", str(intel),
            "--run-id", "nonexistent",
            "--out-dir", str(tmp_path / "briefs"),
            "--rule-based",
        ])
    except SystemExit as exc:
        assert "nonexistent" in str(exc)
    else:
        raise AssertionError("expected SystemExit for unknown run_id")


def test_empty_store_returns_zero(tmp_path):
    rc = main([
        "--intel", str(tmp_path / "missing.jsonl"),
        "--out-dir", str(tmp_path / "briefs"),
    ])
    assert rc == 0


def test_claude_path_used_when_not_rule_based(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out_dir = tmp_path / "briefs"
    _write_jsonl(intel, [
        {"record_id": "r1", "content": "test event", "run_id": "r",
         "written_at": "2026-05-01T00:00:00+00:00"},
    ])
    fake_brief = "# Mocked Claude Brief\n\nThis is the LLM output."
    fake_prompts = "## SYSTEM\n\nfake system\n\n## USER\n\nfake user\n"
    with patch("spec1_core.briefing.generator.generate_brief",
               return_value=(fake_brief, fake_prompts)) as mock_gen:
        rc = main([
            "--intel", str(intel),
            "--run-id", "r",
            "--out-dir", str(out_dir),
        ])
    assert rc == 0
    mock_gen.assert_called_once()
    written = (out_dir / "spec1_brief_latest.md").read_text()
    assert "Mocked Claude Brief" in written
    assert (out_dir / "spec1_prompts_2026-05-01.md").exists()


def test_claude_failure_falls_back(tmp_path):
    intel = tmp_path / "intel.jsonl"
    out_dir = tmp_path / "briefs"
    _write_jsonl(intel, [
        {"record_id": "r1", "content": "test event", "run_id": "r",
         "written_at": "2026-05-01T00:00:00+00:00"},
    ])
    with patch("spec1_core.briefing.generator.generate_brief",
               side_effect=RuntimeError("api dead")):
        rc = main([
            "--intel", str(intel),
            "--run-id", "r",
            "--out-dir", str(out_dir),
        ])
    assert rc == 0
    # Fallback wrote something (rule-based brief)
    assert (out_dir / "spec1_brief_latest.md").exists()
    assert (out_dir / "spec1_brief_latest.md").read_text().strip() != ""
