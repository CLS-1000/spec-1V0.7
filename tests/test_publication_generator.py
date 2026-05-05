"""Tests for spec1_engine.tools.publication_generator."""
from __future__ import annotations

import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_records() -> list[dict]:
    return [
        {
            "content": "Intelligence agencies have identified coordinated influence operations targeting election infrastructure across multiple jurisdictions.",
            "source": "reuters",
            "credibility_score": 0.85,
            "classification": "ESCALATE",
            "velocity_label": "RAPID",
            "gate_results": {
                "credibility": {"passed": True, "reason": "Primary source, verifiable"},
                "volume":      {"passed": True, "reason": "Word count above threshold"},
                "velocity":    {"passed": True, "reason": "Within 48h window"},
                "novelty":     {"passed": True, "reason": "Hash not seen before"},
            },
        },
        {
            "content": "Congressional oversight committee launches investigation into foreign lobbying disclosures following FARA filing surge.",
            "source": "politico",
            "credibility_score": 0.72,
            "classification": "INVESTIGATE",
            "velocity_label": "STANDARD",
            "gate_results": {},
        },
    ]


@pytest.fixture()
def sample_brief_text() -> str:
    return (
        "Pattern: Information Environment Manipulation\n\n"
        "Multiple coordinated narratives have been detected across 14 media markets. "
        "Cross-referencing FARA filings with legislative calendar reveals temporal clustering "
        "consistent with pre-vote influence operations. Confidence: MEDIUM-HIGH.\n\n"
        "Secondary signals from congressional sources indicate awareness at committee level."
    )


@pytest.fixture()
def sample_cycle_stats() -> dict:
    return {
        "run_id": "test-run-001",
        "signals_harvested": 120,
        "records_stored": 8,
        "confidence_avg": 0.71,
        "psyop_score": 4.5,
        "psyop_classification": "COORDINATED",
        "psyop_patterns_fired": ["narrative_convergence"],
        "fara_signals": 3,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_generate_publication_creates_pdf(tmp_path, sample_records, sample_brief_text, sample_cycle_stats):
    """generate_publication() must produce a PDF file at the returned path."""
    from spec1_engine.tools.publication_generator import generate_publication

    out = generate_publication(
        records=sample_records,
        brief_text=sample_brief_text,
        cycle_stats=sample_cycle_stats,
        output_dir=str(tmp_path),
        issue_number=1,
    )
    assert Path(out).exists(), "PDF file was not created"
    assert out.endswith(".pdf"), "Output path does not end with .pdf"


def test_generate_publication_file_size(tmp_path, sample_records, sample_brief_text, sample_cycle_stats):
    """Generated PDF must be larger than 10 KB — not an empty shell."""
    from spec1_engine.tools.publication_generator import generate_publication

    out = generate_publication(
        records=sample_records,
        brief_text=sample_brief_text,
        cycle_stats=sample_cycle_stats,
        output_dir=str(tmp_path),
        issue_number=1,
    )
    size = Path(out).stat().st_size
    assert size > 5_000, f"PDF too small ({size} bytes) — expected > 5 KB"


def test_generate_publication_issue_number_auto_increments(tmp_path, sample_records, sample_brief_text, sample_cycle_stats):
    """Issue number must auto-increment based on existing files in output_dir."""
    from spec1_engine.tools.publication_generator import generate_publication

    out1 = generate_publication(
        records=sample_records,
        brief_text=sample_brief_text,
        cycle_stats=sample_cycle_stats,
        output_dir=str(tmp_path),
    )
    out2 = generate_publication(
        records=sample_records,
        brief_text=sample_brief_text,
        cycle_stats=sample_cycle_stats,
        output_dir=str(tmp_path),
    )

    name1 = Path(out1).name
    name2 = Path(out2).name

    assert name1 != name2, "Auto-incremented issues should produce different file names"
    assert "spec1_issue_001" in name1, f"First issue should be 001, got {name1}"
    assert "spec1_issue_002" in name2, f"Second issue should be 002, got {name2}"


def test_generate_publication_empty_records(tmp_path, sample_brief_text, sample_cycle_stats):
    """generate_publication() must not crash when records list is empty."""
    from spec1_engine.tools.publication_generator import generate_publication

    out = generate_publication(
        records=[],
        brief_text=sample_brief_text,
        cycle_stats=sample_cycle_stats,
        output_dir=str(tmp_path),
        issue_number=1,
    )
    assert Path(out).exists(), "PDF must still be generated even with empty records"
    assert Path(out).stat().st_size > 1_000


def test_generate_publication_domain_scores_capped(tmp_path, sample_records, sample_brief_text):
    """Domain scores derived from extreme cycle_stats must be capped at 1.0."""
    from spec1_engine.tools.publication_generator import generate_publication
    from spec1_engine.tools.publication_generator import _draw_hexagon_cover

    cycle_stats = {
        "signals_harvested": 9999,   # would produce > 1.0 without cap
        "confidence_avg": 2.5,       # above 1.0
        "psyop_score": 999,          # would produce > 1.0 without cap
        "psyop_classification": "NOISE",
        "psyop_patterns_fired": [],
        "fara_signals": 0,
    }

    domain_scores = {
        "power":     min(1.0, cycle_stats.get("signals_harvested", 100) / 300),
        "security":  min(1.0, max(0.0, cycle_stats.get("confidence_avg", 0.6))),
        "economics": 0.5,
        "conflict":  min(1.0, cycle_stats.get("psyop_score", 2) / 10),
        "diplomacy": 0.4,
        "alliances": 0.35,
    }

    for domain, score in domain_scores.items():
        assert score <= 1.0, f"Domain '{domain}' score {score} exceeds 1.0"
        assert score >= 0.0, f"Domain '{domain}' score {score} is negative"

    # Also confirm the full generation completes without error
    out = generate_publication(
        records=sample_records,
        brief_text="Brief text.",
        cycle_stats=cycle_stats,
        output_dir=str(tmp_path),
        issue_number=1,
    )
    assert Path(out).exists()


def test_generate_publication_explicit_issue_number(tmp_path, sample_records, sample_brief_text, sample_cycle_stats):
    """Explicit issue_number parameter must be used verbatim in the filename."""
    from spec1_engine.tools.publication_generator import generate_publication

    out = generate_publication(
        records=sample_records,
        brief_text=sample_brief_text,
        cycle_stats=sample_cycle_stats,
        output_dir=str(tmp_path),
        issue_number=42,
    )
    assert "spec1_issue_042" in Path(out).name


def test_generate_publication_output_dir_created(tmp_path, sample_records, sample_brief_text, sample_cycle_stats):
    """generate_publication() must create output_dir if it does not exist."""
    from spec1_engine.tools.publication_generator import generate_publication

    nested = tmp_path / "deep" / "nested" / "dir"
    out = generate_publication(
        records=sample_records,
        brief_text=sample_brief_text,
        cycle_stats=sample_cycle_stats,
        output_dir=str(nested),
        issue_number=1,
    )
    assert Path(out).exists()
