"""Calibration report dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import List


@dataclass
class CalibrationBucket:
    """Reliability metrics for one slice of the data (e.g. confidence 0.7–0.8)."""

    bucket_label: str
    record_count: int
    verdict_count: int
    tp_count: int
    fp_count: int
    precision: float  # tp / (tp + fp) if (tp+fp) > 0 else None → stored as -1.0
    tp_rate: float    # tp / verdict_count if verdict_count > 0 else -1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AdjustmentProposal:
    """A descriptive suggestion — never auto-applied."""

    dimension: str     # "source_weight" | "analyst_weight" | "confidence_threshold"
    bucket_label: str
    current_value: float
    suggested_value: float
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CalibrationReport:
    report_id: str
    generated_at: str
    record_count: int
    verdict_count: int
    confidence_buckets: List[CalibrationBucket] = field(default_factory=list)
    source_weight_buckets: List[CalibrationBucket] = field(default_factory=list)
    analyst_weight_buckets: List[CalibrationBucket] = field(default_factory=list)
    proposals: List[AdjustmentProposal] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "record_count": self.record_count,
            "verdict_count": self.verdict_count,
            "confidence_buckets": [b.to_dict() for b in self.confidence_buckets],
            "source_weight_buckets": [b.to_dict() for b in self.source_weight_buckets],
            "analyst_weight_buckets": [b.to_dict() for b in self.analyst_weight_buckets],
            "proposals": [p.to_dict() for p in self.proposals],
        }
