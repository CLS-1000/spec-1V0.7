"""Verdict dataclass — human ground-truth label for an intelligence record."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


VALID_OUTCOMES = {"TP", "FP", "TN", "FN", "PARTIAL"}


@dataclass
class Verdict:
    verdict_id: str
    record_id: str
    outcome: str  # TP | FP | TN | FN | PARTIAL
    analyst_id: str = ""
    notes: str = ""
    filed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        if self.outcome not in VALID_OUTCOMES:
            raise ValueError(f"outcome must be one of {VALID_OUTCOMES}, got {self.outcome!r}")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Verdict":
        return cls(
            verdict_id=d["verdict_id"],
            record_id=d["record_id"],
            outcome=d["outcome"],
            analyst_id=d.get("analyst_id", ""),
            notes=d.get("notes", ""),
            filed_at=d.get("filed_at", datetime.now(timezone.utc).isoformat()),
        )
