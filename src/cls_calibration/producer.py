# @domain:   spec-1
# @module:   producer
# @loc:      gh_main
# @status:   stable
# @depends:  NONE

"""Calibration report producer.

Aggregates verdicts onto intelligence records and surfaces reliability drift
across confidence / source_weight / analyst_weight buckets.
All output is descriptive — adjustments are never auto-applied.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from cls_calibration.schemas import (
    AdjustmentProposal,
    CalibrationBucket,
    CalibrationReport,
)
from spec1_labels import VERIF_PARTIAL


def _bucket_label(value: float, step: float = 0.1) -> str:
    low = round(int(value / step) * step, 2)
    high = round(low + step, 2)
    return f"{low:.1f}-{high:.1f}"


def _build_buckets(
    records: list[dict],
    verdicts: list[dict],
    dimension: str,
) -> List[CalibrationBucket]:
    """Slice records by *dimension* into 0.1-wide buckets and compute reliability."""
    verdict_index: dict[str, list[str]] = {}
    for v in verdicts:
        verdict_index.setdefault(v["record_id"], []).append(v["outcome"])

    bucket_data: dict[str, dict] = {}
    for rec in records:
        value = float(rec.get(dimension, 0.0))
        label = _bucket_label(value)
        if label not in bucket_data:
            bucket_data[label] = {"records": 0, "verdicts": 0, "tp": 0, "fp": 0}
        bucket_data[label]["records"] += 1
        outcomes = verdict_index.get(rec.get("record_id", ""), [])
        bucket_data[label]["verdicts"] += len(outcomes)
        bucket_data[label]["tp"] += sum(1 for o in outcomes if o in ("TP", VERIF_PARTIAL))
        bucket_data[label]["fp"] += sum(1 for o in outcomes if o == "FP")

    buckets: List[CalibrationBucket] = []
    for label in sorted(bucket_data):
        d = bucket_data[label]
        tp, fp = d["tp"], d["fp"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else -1.0
        tp_rate = tp / d["verdicts"] if d["verdicts"] > 0 else -1.0
        buckets.append(CalibrationBucket(
            bucket_label=label,
            record_count=d["records"],
            verdict_count=d["verdicts"],
            tp_count=tp,
            fp_count=fp,
            precision=precision,
            tp_rate=tp_rate,
        ))
    return buckets


def produce_report(
    records: list[dict],
    verdicts: list[dict],
    include_proposals: bool = False,
) -> CalibrationReport:
    """Aggregate verdicts onto records and build a CalibrationReport.

    Args:
        records: intelligence records (dicts with record_id, confidence,
                 source_weight, analyst_weight).
        verdicts: verdict dicts (verdict_id, record_id, outcome, …).
        include_proposals: if True, populate report.proposals.
    """
    report = CalibrationReport(
        report_id=str(uuid.uuid4()),
        generated_at=datetime.now(timezone.utc).isoformat(),
        record_count=len(records),
        verdict_count=len(verdicts),
        confidence_buckets=_build_buckets(records, verdicts, "confidence"),
        source_weight_buckets=_build_buckets(records, verdicts, "source_weight"),
        analyst_weight_buckets=_build_buckets(records, verdicts, "analyst_weight"),
    )
    if include_proposals:
        report.proposals = propose_adjustments(report)
    return report


def propose_adjustments(report: CalibrationReport) -> List[AdjustmentProposal]:
    """Emit descriptive suggestions based on reliability drift.

    Suggestions are NEVER auto-applied — they are for human review only.
    A bucket with fewer than 3 verdicts is skipped (insufficient data).
    """
    proposals: List[AdjustmentProposal] = []
    MIN_VERDICTS = 3

    def _check_buckets(buckets: List[CalibrationBucket], dimension: str) -> None:
        for b in buckets:
            if b.verdict_count < MIN_VERDICTS or b.precision < 0:
                continue
            # If precision deviates more than 0.2 from the bucket mid-point
            # (i.e. the model is over- or under-confident), surface a suggestion.
            parts = b.bucket_label.split("-")
            if len(parts) == 2:
                try:
                    mid = (float(parts[0]) + float(parts[1])) / 2.0
                except ValueError:
                    continue
                delta = b.precision - mid
                if abs(delta) >= 0.2:
                    suggested = round(mid + delta * 0.5, 2)
                    proposals.append(AdjustmentProposal(
                        dimension=dimension,
                        bucket_label=b.bucket_label,
                        current_value=mid,
                        suggested_value=max(0.0, min(1.0, suggested)),
                        reason=(
                            f"Observed precision {b.precision:.2f} deviates "
                            f"{delta:+.2f} from bucket midpoint {mid:.2f} "
                            f"({b.verdict_count} verdicts, {b.tp_count} TP, {b.fp_count} FP)"
                        ),
                    ))

    _check_buckets(report.confidence_buckets, "confidence_threshold")
    _check_buckets(report.source_weight_buckets, "source_weight")
    _check_buckets(report.analyst_weight_buckets, "analyst_weight")
    return proposals
