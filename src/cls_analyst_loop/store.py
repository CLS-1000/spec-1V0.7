# @domain:   spec-1
# @module:   store
# @loc:      _SCRATCH
# @status:   drafting
# @depends:  cls_db

"""Append-only JSONL + SQLite dual-write storage for analyst workflow records.

All four record types (case, output, audit, verdict) persist via:
- JSONL (append-only, source of truth)
- SQLite (queryable, optional)

Thread-safe writes enforce single-writer rule.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from cls_analyst_loop.schemas import (
    AnalystCase,
    AnalystOutput,
    AnalystVerdict,
    AuditResult,
)

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnalystLoopStore:
    """Thread-safe append-only dual-write storage for analyst workflow."""

    def __init__(
        self,
        base_path: Path = Path("analyst_loop"),
        db: Optional["Database"] = None,  # noqa: F821
    ) -> None:
        self.base_path = Path(base_path)
        self.cases_path = self.base_path / "cases.jsonl"
        self.outputs_path = self.base_path / "outputs.jsonl"
        self.audits_path = self.base_path / "audits.jsonl"
        self.verdicts_path = self.base_path / "verdicts.jsonl"

        self._lock = threading.Lock()
        self._dual_writer = None

        if db is not None:
            from cls_db.dual_write import DualWriter

            self._dual_writer = {
                "cases": DualWriter(
                    jsonl_path=self.cases_path,
                    db=db,
                    table="analyst_cases",
                    pk_field="case_id",
                ),
                "outputs": DualWriter(
                    jsonl_path=self.outputs_path,
                    db=db,
                    table="analyst_outputs",
                    pk_field="output_id",
                ),
                "audits": DualWriter(
                    jsonl_path=self.audits_path,
                    db=db,
                    table="audit_results",
                    pk_field="audit_id",
                ),
                "verdicts": DualWriter(
                    jsonl_path=self.verdicts_path,
                    db=db,
                    table="analyst_verdicts",
                    pk_field="verdict_id",
                ),
            }

    def save_case(self, case: AnalystCase) -> dict:
        """Append a case to cases.jsonl (+ SQLite if configured)."""
        if self._dual_writer is not None:
            return self._dual_writer["cases"].write(case.to_dict())

        entry = {**case.to_dict(), "written_at": _now()}
        with self._lock:
            self.cases_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cases_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        return entry

    def save_output(self, output: AnalystOutput) -> dict:
        """Append an output to outputs.jsonl (+ SQLite if configured)."""
        if self._dual_writer is not None:
            return self._dual_writer["outputs"].write(output.to_dict())

        entry = {**output.to_dict(), "written_at": _now()}
        with self._lock:
            self.outputs_path.parent.mkdir(parents=True, exist_ok=True)
            with self.outputs_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        return entry

    def save_audit(self, audit: AuditResult) -> dict:
        """Append an audit to audits.jsonl (+ SQLite if configured)."""
        if self._dual_writer is not None:
            return self._dual_writer["audits"].write(audit.to_dict())

        entry = {**audit.to_dict(), "written_at": _now()}
        with self._lock:
            self.audits_path.parent.mkdir(parents=True, exist_ok=True)
            with self.audits_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        return entry

    def save_verdict(self, verdict: AnalystVerdict) -> dict:
        """Append a verdict to verdicts.jsonl (+ SQLite if configured)."""
        if self._dual_writer is not None:
            return self._dual_writer["verdicts"].write(verdict.to_dict())

        entry = {**verdict.to_dict(), "written_at": _now()}
        with self._lock:
            self.verdicts_path.parent.mkdir(parents=True, exist_ok=True)
            with self.verdicts_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        return entry

    def read_cases(self) -> Iterator[dict]:
        """Yield all cases from cases.jsonl."""
        if not self.cases_path.exists():
            return
        with self.cases_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def read_outputs(self) -> Iterator[dict]:
        """Yield all outputs from outputs.jsonl."""
        if not self.outputs_path.exists():
            return
        with self.outputs_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def read_audits(self) -> Iterator[dict]:
        """Yield all audits from audits.jsonl."""
        if not self.audits_path.exists():
            return
        with self.audits_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def read_verdicts(self) -> Iterator[dict]:
        """Yield all verdicts from verdicts.jsonl."""
        if not self.verdicts_path.exists():
            return
        with self.verdicts_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def get_case(self, case_id: str) -> Optional[dict]:
        """Fetch a single case by ID."""
        for case in self.read_cases():
            if case.get("case_id") == case_id:
                return case
        return None

    def get_output(self, output_id: str) -> Optional[dict]:
        """Fetch a single output by ID."""
        for output in self.read_outputs():
            if output.get("output_id") == output_id:
                return output
        return None

    def get_audit(self, audit_id: str) -> Optional[dict]:
        """Fetch a single audit by ID."""
        for audit in self.read_audits():
            if audit.get("audit_id") == audit_id:
                return audit
        return None

    def get_verdict(self, verdict_id: str) -> Optional[dict]:
        """Fetch a single verdict by ID."""
        for verdict in self.read_verdicts():
            if verdict.get("verdict_id") == verdict_id:
                return verdict
        return None

    def outputs_for_case(self, case_id: str) -> list[dict]:
        """All outputs filed for a case."""
        return [o for o in self.read_outputs() if o.get("case_id") == case_id]

    def audits_for_output(self, output_id: str) -> list[dict]:
        """All audits filed for an output."""
        return [a for a in self.read_audits() if a.get("output_id") == output_id]

    def verdicts_for_case(self, case_id: str) -> list[dict]:
        """All verdicts filed for a case."""
        return [v for v in self.read_verdicts() if v.get("case_id") == case_id]

    def list_cases(
        self, lead_id: Optional[str] = None, analyst_id: Optional[str] = None
    ) -> list[dict]:
        """List cases with optional filtering."""
        cases = list(self.read_cases())
        if lead_id:
            cases = [c for c in cases if c.get("lead_id") == lead_id]
        if analyst_id:
            cases = [c for c in cases if c.get("analyst_id") == analyst_id]
        return cases

    def count_cases(self) -> int:
        return sum(1 for _ in self.read_cases())

    def count_outputs(self) -> int:
        return sum(1 for _ in self.read_outputs())

    def count_audits(self) -> int:
        return sum(1 for _ in self.read_audits())

    def count_verdicts(self) -> int:
        return sum(1 for _ in self.read_verdicts())
