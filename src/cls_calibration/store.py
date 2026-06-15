# @domain:   spec-1
# @module:   store
# @loc:      _SCRATCH
# @status:   drafting
# @depends:  NONE

"""JSONL persistence for CalibrationReport."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from cls_calibration.schemas import CalibrationReport


class CalibrationStore:
    def __init__(self, jsonl_path: Path) -> None:
        self._path = Path(jsonl_path)
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, report: CalibrationReport) -> None:
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(report.to_dict()) + "\n")

    def latest(self) -> CalibrationReport | None:
        if not self._path.exists():
            return None
        last_line = ""
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last_line = line.strip()
        if not last_line:
            return None
        try:
            d = json.loads(last_line)
        except json.JSONDecodeError:
            return None
        from cls_calibration.schemas import (
            AdjustmentProposal, CalibrationBucket,
        )

        def _bucket(b: dict) -> CalibrationBucket:
            return CalibrationBucket(
                bucket_label=b["bucket_label"],
                record_count=b["record_count"],
                verdict_count=b["verdict_count"],
                tp_count=b["tp_count"],
                fp_count=b["fp_count"],
                precision=b["precision"],
                tp_rate=b["tp_rate"],
            )

        return CalibrationReport(
            report_id=d["report_id"],
            generated_at=d["generated_at"],
            record_count=d["record_count"],
            verdict_count=d["verdict_count"],
            confidence_buckets=[_bucket(b) for b in d.get("confidence_buckets", [])],
            source_weight_buckets=[_bucket(b) for b in d.get("source_weight_buckets", [])],
            analyst_weight_buckets=[_bucket(b) for b in d.get("analyst_weight_buckets", [])],
            proposals=[
                AdjustmentProposal(**p) for p in d.get("proposals", [])
            ],
        )
