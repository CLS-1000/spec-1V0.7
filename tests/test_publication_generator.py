"""Tests for spec1_engine.tools.publication_generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from spec1_engine.tools.publication_generator import generate_publication


_SAMPLE_RECORDS = [
    {
        "content": "Russia deploys additional forces near border region amid diplomatic tensions.",
        "source": "reuters",
        "credibility_score": 0.85,
        "classification": "ESCALATE",
        "velocity_label": "HIGH",
        "gate_results": {
            "Credibility": True,
            "Volume": True,
            "Velocity": True,
            "Novelty": True,
        },
    },
    {
        "content": "Senate committee advances foreign lobbying reform bill following FARA review.",
        "source": "ap",
        "credibility_score": 0.72,
        "classification": "INVESTIGATE",
        "velocity_label": "STANDARD",
    },
]

_SAMPLE_BRIEF = (
    "SIGNAL CONVERGENCE DETECTED across multiple geopolitical domains. "
    "Cross-domain activity suggests coordinated narrative pressure originating from state-adjacent actors. "
    "Congressional activity shows elevated FARA-adjacent lobbying patterns. "
    "Confidence level: MEDIUM-HIGH. Recommend continued monitoring."
)

_SAMPLE_STATS = {
    "signals_harvested": 120,
    "records_stored": 18,
    "confidence_avg": 0.71,
    "psyop_score": 4.2,
    "psyop_classification": "COORDINATED",
    "psyop_patterns_fired": ["narrative_flood", "source_convergence"],
    "fara_signals": 3,
}


def test_generate_publication_creates_pdf(tmp_path):
    """generate_publication() produces a PDF file at the expected path."""
    out = generate_publication(
        records=_SAMPLE_RECORDS,
        brief_text=_SAMPLE_BRIEF,
        cycle_stats=_SAMPLE_STATS,
        output_dir=str(tmp_path),
        issue_number=1,
    )
    assert Path(out).exists(), f"Expected PDF at {out}"
    assert out.endswith(".pdf")


def test_generate_publication_file_size(tmp_path):
    """Generated PDF is larger than 5 KB."""
    out = generate_publication(
        records=_SAMPLE_RECORDS,
        brief_text=_SAMPLE_BRIEF,
        cycle_stats=_SAMPLE_STATS,
        output_dir=str(tmp_path),
        issue_number=1,
    )
    size = Path(out).stat().st_size
    assert size > 5_000, f"PDF too small: {size} bytes"


def test_generate_publication_issue_number_auto_increments(tmp_path):
    """Issue number auto-increments based on existing PDFs in output_dir."""
    # First run — no existing PDFs → issue 001
    out1 = generate_publication(
        records=_SAMPLE_RECORDS,
        brief_text=_SAMPLE_BRIEF,
        cycle_stats=_SAMPLE_STATS,
        output_dir=str(tmp_path),
    )
    assert "spec1_issue_001_" in Path(out1).name

    # Second run — one existing PDF → issue 002
    out2 = generate_publication(
        records=_SAMPLE_RECORDS,
        brief_text=_SAMPLE_BRIEF,
        cycle_stats=_SAMPLE_STATS,
        output_dir=str(tmp_path),
    )
    assert "spec1_issue_002_" in Path(out2).name


def test_generate_publication_empty_records(tmp_path):
    """Falls back gracefully when records list is empty."""
    out = generate_publication(
        records=[],
        brief_text="",
        cycle_stats={},
        output_dir=str(tmp_path),
        issue_number=1,
    )
    assert Path(out).exists()
    assert Path(out).stat().st_size > 1_000


def test_generate_publication_domain_scores_capped(tmp_path):
    """Domain scores derived from cycle_stats are capped at 1.0."""
    # signals_harvested=9000 would produce power > 1.0 without capping
    stats = {**_SAMPLE_STATS, "signals_harvested": 9000, "psyop_score": 999}
    out = generate_publication(
        records=_SAMPLE_RECORDS,
        brief_text=_SAMPLE_BRIEF,
        cycle_stats=stats,
        output_dir=str(tmp_path),
        issue_number=1,
    )
    # If domain scores weren't capped reportlab would raise on values > 1.0
    # causing Polygon rendering to fail; a valid PDF means the cap worked.
    assert Path(out).exists()
    assert Path(out).stat().st_size > 5_000
