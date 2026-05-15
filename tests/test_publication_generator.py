"""Tests for spec1_engine.tools.publication_generator."""
from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_records() -> list[dict]:
    return [
        {
            "content": (
                "Intelligence agencies have identified coordinated influence operations"
                " targeting election infrastructure across multiple jurisdictions."
            ),
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
            "content": (
                "Congressional oversight committee launches investigation into foreign"
                " lobbying disclosures following FARA filing surge."
            ),
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
    """Generated file must be a valid PDF (starts with %PDF-) and non-trivially sized."""
    from spec1_engine.tools.publication_generator import generate_publication

    out = generate_publication(
        records=sample_records,
        brief_text=sample_brief_text,
        cycle_stats=sample_cycle_stats,
        output_dir=str(tmp_path),
        issue_number=1,
    )
    header = Path(out).read_bytes()[:5]
    assert header == b'%PDF-', f"File does not start with PDF magic bytes: {header!r}"
    assert Path(out).stat().st_size > 5_000, "PDF is unexpectedly small"


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
    """_derive_domain_scores() must cap all values to [0.0, 1.0] regardless of inputs."""
    from spec1_engine.tools.publication_generator import generate_publication, _derive_domain_scores

    cycle_stats = {
        "signals_harvested": 9999,   # would produce > 1.0 without cap
        "confidence_avg": 2.5,       # above 1.0
        "psyop_score": 999,          # would produce > 1.0 without cap
        "psyop_classification": "NOISE",
        "psyop_patterns_fired": [],
        "fara_signals": 0,
    }

    domain_scores = _derive_domain_scores(cycle_stats)

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


def test_generate_publication_bool_gate_results(tmp_path, sample_brief_text, sample_cycle_stats):
    """Records with bool gate_results (real engine shape) must not raise AttributeError."""
    from spec1_engine.tools.publication_generator import generate_publication

    records_with_bool_gates = [
        {
            "content": "Foreign state actors coordinated disinformation across social platforms ahead of scheduled elections.",
            "source": "ap",
            "credibility_score": 0.88,
            "velocity_label": "RAPID",
            "gate_results": {
                "credibility": True,
                "volume": True,
                "velocity": True,
                "novelty": True,
            },
        },
        {
            "content": "Sanctions package targets energy sector financing linked to sanctioned entities.",
            "source": "reuters",
            "credibility_score": 0.65,
            "velocity_label": "STANDARD",
            "gate_results": {
                "credibility": True,
                "volume": False,
                "velocity": True,
                "novelty": True,
            },
        },
    ]
    out = generate_publication(
        records=records_with_bool_gates,
        brief_text=sample_brief_text,
        cycle_stats=sample_cycle_stats,
        output_dir=str(tmp_path),
        issue_number=1,
    )
    assert Path(out).exists()
    assert Path(out).stat().st_size > 1_000


# ---------------------------------------------------------------------------
# API router tests
# ---------------------------------------------------------------------------

def test_publication_latest_returns_404_when_no_pdfs(tmp_path, monkeypatch):
    """GET /publication/latest must return 404 when generated/briefs has no PDFs."""
    import spec1_api.routers.publication as pub_mod
    monkeypatch.setattr(pub_mod, '_BRIEFS_DIR', tmp_path)

    from fastapi.testclient import TestClient
    from spec1_api.main import create_app
    client = TestClient(create_app())
    resp = client.get('/publication/latest')
    assert resp.status_code == 404


def test_publication_list_returns_stable_shape(tmp_path, monkeypatch, sample_records, sample_brief_text, sample_cycle_stats):
    """GET /publication/list must return {total, items} and order newest first."""
    from spec1_engine.tools.publication_generator import generate_publication
    import spec1_api.routers.publication as pub_mod
    monkeypatch.setattr(pub_mod, '_BRIEFS_DIR', tmp_path)

    # Generate two PDFs with different issue numbers.
    generate_publication(
        records=sample_records,
        brief_text=sample_brief_text,
        cycle_stats=sample_cycle_stats,
        output_dir=str(tmp_path),
        issue_number=1,
    )
    generate_publication(
        records=sample_records,
        brief_text=sample_brief_text,
        cycle_stats=sample_cycle_stats,
        output_dir=str(tmp_path),
        issue_number=2,
    )

    from fastapi.testclient import TestClient
    from spec1_api.main import create_app
    client = TestClient(create_app())
    resp = client.get('/publication/list')
    assert resp.status_code == 200
    body = resp.json()
    assert 'total' in body
    assert 'items' in body
    assert body['total'] == 2
    assert len(body['items']) == 2
    # Newest first — issue 002 should appear before issue 001.
    assert 'spec1_issue_002' in body['items'][0]['filename']
