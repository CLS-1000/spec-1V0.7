"""GET /calibration"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from spec1_api.dependencies import (
    get_intel_store, get_verdict_store,
    IntelStoreDep, VerdictStoreDep,
)

router = APIRouter(prefix="/calibration", tags=["calibration"])


@router.get("/")
def get_calibration(
    include_proposals: bool = False,
    intel_store: IntelStoreDep = Depends(get_intel_store),  # type: ignore[assignment]
    verdict_store: VerdictStoreDep = Depends(get_verdict_store),  # type: ignore[assignment]
) -> dict:
    from cls_calibration.producer import produce_report

    records = _load_records(intel_store)
    verdicts = [v.to_dict() for v in verdict_store.read_all(limit=50_000)]
    report = produce_report(records, verdicts, include_proposals=include_proposals)
    return report.to_dict()


def _load_records(intel_store) -> list[dict]:  # type: ignore[type-arg]
    try:
        items = intel_store.read_all(limit=10_000)  # type: ignore[attr-defined]
        return [r if isinstance(r, dict) else r.to_dict() for r in items]
    except Exception:
        return []
