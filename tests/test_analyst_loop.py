"""Tests for cls_analyst_loop — analyst workflow chain of custody."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cls_analyst_loop.schemas import (
    AnalystCase,
    AnalystOutput,
    AnalystVerdict,
    AuditResult,
)
from cls_analyst_loop.store import AnalystLoopStore


@pytest.fixture
def tmp_store(tmp_path: Path) -> AnalystLoopStore:
    """Create a temporary analyst loop store."""
    return AnalystLoopStore(base_path=tmp_path / "analyst_loop")


class TestAnalystCaseSchema:
    """Test AnalystCase dataclass."""

    def test_create_case(self) -> None:
        """Create a case with all required fields."""
        now = datetime.now(timezone.utc)
        case_id = AnalystCase.make_id("lead_123", "analyst_01", now)
        case = AnalystCase(
            case_id=case_id,
            run_id="run_001",
            lead_id="lead_123",
            lead_text="Some lead content",
            feed_prompt="Feed this data to Claude",
            analyst_id="analyst_01",
            created_at=now,
        )
        assert case.case_id.startswith("case_")
        assert case.run_id == "run_001"
        assert case.lead_id == "lead_123"

    def test_case_to_dict(self) -> None:
        """Convert case to dict."""
        now = datetime.now(timezone.utc)
        case_id = AnalystCase.make_id("lead_1", "analyst_1", now)
        case = AnalystCase(
            case_id=case_id,
            run_id="run_001",
            lead_id="lead_1",
            lead_text="text",
            feed_prompt="prompt",
            analyst_id="analyst_1",
            created_at=now,
        )
        d = case.to_dict()
        assert d["case_id"] == case_id
        assert d["schema_version"] == 1
        assert isinstance(d["created_at"], str)


class TestAnalystOutputSchema:
    """Test AnalystOutput dataclass."""

    def test_create_output(self) -> None:
        """Create output."""
        now = datetime.now(timezone.utc)
        output_id = AnalystOutput.make_id("case_123", now)
        output = AnalystOutput(
            output_id=output_id,
            case_id="case_123",
            raw_output="Full analyst report text",
            source_data="Source data provided",
            submitted_at=now,
        )
        assert output.output_id.startswith("output_")
        assert output.case_id == "case_123"

    def test_output_to_dict(self) -> None:
        """Convert output to dict."""
        now = datetime.now(timezone.utc)
        output_id = AnalystOutput.make_id("case_1", now)
        output = AnalystOutput(
            output_id=output_id,
            case_id="case_1",
            raw_output="report",
            source_data="sources",
            submitted_at=now,
        )
        d = output.to_dict()
        assert d["output_id"] == output_id
        assert d["case_id"] == "case_1"


class TestAuditResultSchema:
    """Test AuditResult dataclass."""

    def test_create_audit(self) -> None:
        """Create audit result."""
        now = datetime.now(timezone.utc)
        audit_id = AuditResult.make_id("output_123", "claude", now)
        audit = AuditResult(
            audit_id=audit_id,
            output_id="output_123",
            audit_llm="claude",
            audit_prompt="audit prompt text",
            claims_confirmed=5,
            claims_flagged=2,
            claims_dropped=1,
            audit_output=json.dumps({"findings": []}),
            confidence=0.85,
            audited_at=now,
        )
        assert audit.audit_id.startswith("audit_")
        assert audit.claims_confirmed == 5
        assert audit.confidence == 0.85

    def test_audit_to_dict(self) -> None:
        """Convert audit to dict."""
        now = datetime.now(timezone.utc)
        audit_id = AuditResult.make_id("output_1", "claude", now)
        audit = AuditResult(
            audit_id=audit_id,
            output_id="output_1",
            audit_llm="claude",
            audit_prompt="prompt",
            claims_confirmed=3,
            claims_flagged=1,
            claims_dropped=0,
            audit_output="{}",
            confidence=0.9,
            audited_at=now,
        )
        d = audit.to_dict()
        assert d["audit_id"] == audit_id
        assert d["claims_confirmed"] == 3


class TestAnalystVerdictSchema:
    """Test AnalystVerdict dataclass."""

    def test_create_verdict(self) -> None:
        """Create verdict."""
        now = datetime.now(timezone.utc)
        verdict_id = AnalystVerdict.make_id("case_123", "reviewer_01", now)
        verdict = AnalystVerdict(
            verdict_id=verdict_id,
            case_id="case_123",
            output_id="output_456",
            audit_id=None,
            kind="confirmed",
            reviewer="reviewer_01",
            notes="Looks good",
            published=True,
            filed_at=now,
        )
        assert verdict.verdict_id.startswith("verdict_")
        assert verdict.kind == "confirmed"
        assert verdict.published is True

    def test_verdict_invalid_kind(self) -> None:
        """Reject invalid verdict kind."""
        with pytest.raises(ValueError):
            AnalystVerdict(
                verdict_id="v_123",
                case_id="case_1",
                output_id="output_1",
                audit_id=None,
                kind="invalid_kind",  # type: ignore
                reviewer="reviewer",
                notes="",
                published=False,
            )

    def test_verdict_to_dict(self) -> None:
        """Convert verdict to dict."""
        now = datetime.now(timezone.utc)
        verdict_id = AnalystVerdict.make_id("case_1", "reviewer", now)
        verdict = AnalystVerdict(
            verdict_id=verdict_id,
            case_id="case_1",
            output_id="output_1",
            audit_id="audit_1",
            kind="partial",
            reviewer="reviewer",
            notes="notes",
            published=False,
            filed_at=now,
        )
        d = verdict.to_dict()
        assert d["kind"] == "partial"
        assert d["published"] is False


class TestAnalystLoopStore:
    """Test AnalystLoopStore JSONL operations."""

    def test_save_and_read_case(self, tmp_store: AnalystLoopStore) -> None:
        """Save and read a case."""
        now = datetime.now(timezone.utc)
        case_id = AnalystCase.make_id("lead_1", "analyst_1", now)
        case = AnalystCase(
            case_id=case_id,
            run_id="run_1",
            lead_id="lead_1",
            lead_text="lead text",
            feed_prompt="feed prompt",
            analyst_id="analyst_1",
            created_at=now,
        )
        tmp_store.save_case(case)
        retrieved = tmp_store.get_case(case_id)
        assert retrieved is not None
        assert retrieved["case_id"] == case_id
        assert retrieved["lead_id"] == "lead_1"

    def test_save_and_read_output(self, tmp_store: AnalystLoopStore) -> None:
        """Save and read an output."""
        now = datetime.now(timezone.utc)
        output_id = AnalystOutput.make_id("case_1", now)
        output = AnalystOutput(
            output_id=output_id,
            case_id="case_1",
            raw_output="output text",
            source_data="source",
            submitted_at=now,
        )
        tmp_store.save_output(output)
        retrieved = tmp_store.get_output(output_id)
        assert retrieved is not None
        assert retrieved["output_id"] == output_id
        assert retrieved["case_id"] == "case_1"

    def test_save_and_read_audit(self, tmp_store: AnalystLoopStore) -> None:
        """Save and read an audit."""
        now = datetime.now(timezone.utc)
        audit_id = AuditResult.make_id("output_1", "claude", now)
        audit = AuditResult(
            audit_id=audit_id,
            output_id="output_1",
            audit_llm="claude",
            audit_prompt="prompt",
            claims_confirmed=2,
            claims_flagged=1,
            claims_dropped=0,
            audit_output="{}",
            confidence=0.8,
            audited_at=now,
        )
        tmp_store.save_audit(audit)
        retrieved = tmp_store.get_audit(audit_id)
        assert retrieved is not None
        assert retrieved["audit_id"] == audit_id
        assert retrieved["claims_confirmed"] == 2

    def test_save_and_read_verdict(self, tmp_store: AnalystLoopStore) -> None:
        """Save and read a verdict."""
        now = datetime.now(timezone.utc)
        verdict_id = AnalystVerdict.make_id("case_1", "reviewer", now)
        verdict = AnalystVerdict(
            verdict_id=verdict_id,
            case_id="case_1",
            output_id="output_1",
            audit_id=None,
            kind="confirmed",
            reviewer="reviewer",
            notes="ok",
            published=True,
            filed_at=now,
        )
        tmp_store.save_verdict(verdict)
        retrieved = tmp_store.get_verdict(verdict_id)
        assert retrieved is not None
        assert retrieved["kind"] == "confirmed"
        assert retrieved["published"] is True

    def test_outputs_for_case(self, tmp_store: AnalystLoopStore) -> None:
        """Get all outputs for a case."""
        now = datetime.now(timezone.utc)
        case_id = "case_abc"

        # Save multiple outputs for same case
        for i in range(3):
            output_id = AnalystOutput.make_id(case_id, now)
            output = AnalystOutput(
                output_id=output_id,
                case_id=case_id,
                raw_output=f"output {i}",
                source_data="source",
                submitted_at=now,
            )
            tmp_store.save_output(output)

        outputs = tmp_store.outputs_for_case(case_id)
        assert len(outputs) == 3
        assert all(o["case_id"] == case_id for o in outputs)

    def test_audits_for_output(self, tmp_store: AnalystLoopStore) -> None:
        """Get all audits for an output."""
        now = datetime.now(timezone.utc)
        output_id = "output_xyz"

        # Save multiple audits for same output
        for i in range(2):
            audit_id = AuditResult.make_id(output_id, "claude", now)
            audit = AuditResult(
                audit_id=audit_id,
                output_id=output_id,
                audit_llm="claude",
                audit_prompt="prompt",
                claims_confirmed=i,
                claims_flagged=0,
                claims_dropped=0,
                audit_output="{}",
                confidence=0.8,
                audited_at=now,
            )
            tmp_store.save_audit(audit)

        audits = tmp_store.audits_for_output(output_id)
        assert len(audits) == 2
        assert all(a["output_id"] == output_id for a in audits)

    def test_verdicts_for_case(self, tmp_store: AnalystLoopStore) -> None:
        """Get all verdicts for a case."""
        now = datetime.now(timezone.utc)
        case_id = "case_123"

        # Save multiple verdicts for same case
        for kind in ["confirmed", "partial"]:
            verdict_id = AnalystVerdict.make_id(case_id, "reviewer", now)
            verdict = AnalystVerdict(
                verdict_id=verdict_id,
                case_id=case_id,
                output_id="output_1",
                audit_id=None,
                kind=kind,  # type: ignore
                reviewer="reviewer",
                notes="",
                published=False,
                filed_at=now,
            )
            tmp_store.save_verdict(verdict)

        verdicts = tmp_store.verdicts_for_case(case_id)
        assert len(verdicts) == 2
        assert all(v["case_id"] == case_id for v in verdicts)

    def test_list_cases(self, tmp_store: AnalystLoopStore) -> None:
        """List cases with filtering."""
        now = datetime.now(timezone.utc)

        # Create cases with different leads and analysts
        for lead_id in ["lead_1", "lead_2"]:
            for analyst_id in ["analyst_a", "analyst_b"]:
                case_id = AnalystCase.make_id(lead_id, analyst_id, now)
                case = AnalystCase(
                    case_id=case_id,
                    run_id="run_1",
                    lead_id=lead_id,
                    lead_text="text",
                    feed_prompt="prompt",
                    analyst_id=analyst_id,
                    created_at=now,
                )
                tmp_store.save_case(case)

        # List all
        all_cases = tmp_store.list_cases()
        assert len(all_cases) == 4

        # Filter by lead
        lead_cases = tmp_store.list_cases(lead_id="lead_1")
        assert len(lead_cases) == 2
        assert all(c["lead_id"] == "lead_1" for c in lead_cases)

        # Filter by analyst
        analyst_cases = tmp_store.list_cases(analyst_id="analyst_a")
        assert len(analyst_cases) == 2
        assert all(c["analyst_id"] == "analyst_a" for c in analyst_cases)

    def test_count_records(self, tmp_store: AnalystLoopStore) -> None:
        """Count records by type."""
        now = datetime.now(timezone.utc)

        # Save one of each
        case_id = AnalystCase.make_id("l1", "a1", now)
        tmp_store.save_case(
            AnalystCase(
                case_id=case_id,
                run_id="run",
                lead_id="l1",
                lead_text="text",
                feed_prompt="prompt",
                analyst_id="a1",
            )
        )

        output_id = AnalystOutput.make_id(case_id, now)
        tmp_store.save_output(
            AnalystOutput(
                output_id=output_id,
                case_id=case_id,
                raw_output="output",
                source_data="source",
            )
        )

        audit_id = AuditResult.make_id(output_id, "claude", now)
        tmp_store.save_audit(
            AuditResult(
                audit_id=audit_id,
                output_id=output_id,
                audit_llm="claude",
                audit_prompt="prompt",
                claims_confirmed=1,
                claims_flagged=0,
                claims_dropped=0,
                audit_output="{}",
                confidence=0.8,
            )
        )

        verdict_id = AnalystVerdict.make_id(case_id, "reviewer", now)
        tmp_store.save_verdict(
            AnalystVerdict(
                verdict_id=verdict_id,
                case_id=case_id,
                output_id=output_id,
                audit_id=audit_id,
                kind="confirmed",
                reviewer="reviewer",
                notes="",
                published=True,
            )
        )

        assert tmp_store.count_cases() == 1
        assert tmp_store.count_outputs() == 1
        assert tmp_store.count_audits() == 1
        assert tmp_store.count_verdicts() == 1


class TestAnalystLoopWorkflow:
    """Integration tests for full workflow."""

    def test_case_to_output_to_audit_to_verdict(self, tmp_store: AnalystLoopStore) -> None:
        """End-to-end workflow: case -> output -> audit -> verdict."""
        now = datetime.now(timezone.utc)

        # Step 1: Create case from lead
        case_id = AnalystCase.make_id("lead_demo", "alice", now)
        case = AnalystCase(
            case_id=case_id,
            run_id="run_001",
            lead_id="lead_demo",
            lead_text="A story about economic signals",
            feed_prompt="Analyze this market data",
            analyst_id="alice",
            created_at=now,
        )
        tmp_store.save_case(case)
        assert tmp_store.get_case(case_id) is not None

        # Step 2: Submit analyst output
        output_id = AnalystOutput.make_id(case_id, now)
        output = AnalystOutput(
            output_id=output_id,
            case_id=case_id,
            raw_output="Analyst concluded XYZ based on ABC",
            source_data="Market data from Reuters",
            submitted_at=now,
        )
        tmp_store.save_output(output)
        assert tmp_store.get_output(output_id) is not None

        # Step 3: Run audit (simulated)
        audit_id = AuditResult.make_id(output_id, "claude", now)
        audit = AuditResult(
            audit_id=audit_id,
            output_id=output_id,
            audit_llm="claude",
            audit_prompt="Check for unsourced claims",
            claims_confirmed=2,
            claims_flagged=1,
            claims_dropped=0,
            audit_output=json.dumps(
                {
                    "claims_confirmed": 2,
                    "claims_flagged": 1,
                    "findings": [
                        {
                            "claim": "XYZ is trending",
                            "problem": "No source cited",
                            "severity": "MEDIUM",
                            "suggested_edit": "Add source",
                        }
                    ],
                }
            ),
            confidence=0.75,
            audited_at=now,
        )
        tmp_store.save_audit(audit)
        assert tmp_store.get_audit(audit_id) is not None

        # Step 4: File verdict
        verdict_id = AnalystVerdict.make_id(case_id, "bob", now)
        verdict = AnalystVerdict(
            verdict_id=verdict_id,
            case_id=case_id,
            output_id=output_id,
            audit_id=audit_id,
            kind="partial",
            reviewer="bob",
            notes="Flagged claim needs source; otherwise sound",
            published=True,
            filed_at=now,
        )
        tmp_store.save_verdict(verdict)
        assert tmp_store.get_verdict(verdict_id) is not None

        # Verify chain of custody
        case_check = tmp_store.get_case(case_id)
        assert case_check is not None

        outputs = tmp_store.outputs_for_case(case_id)
        assert len(outputs) == 1
        assert outputs[0]["output_id"] == output_id

        audits = tmp_store.audits_for_output(output_id)
        assert len(audits) == 1
        assert audits[0]["audit_id"] == audit_id

        verdicts = tmp_store.verdicts_for_case(case_id)
        assert len(verdicts) == 1
        assert verdicts[0]["published"] is True
