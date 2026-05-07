"""GET /verdicts  POST /verdicts"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from spec1_api.dependencies import get_verdict_store, VerdictStoreDep

router = APIRouter(prefix="/verdicts", tags=["verdicts"])


class VerdictRequest(BaseModel):
    record_id: str
    outcome: str
    analyst_id: str = ""
    notes: str = ""


@router.get("/")
def list_verdicts(
    record_id: Optional[str] = None,
    limit: int = 50,
    store: VerdictStoreDep = Depends(get_verdict_store),  # type: ignore[assignment]
) -> list[dict]:
    if record_id:
        return [v.to_dict() for v in store.read_for_record(record_id)]
    return [v.to_dict() for v in store.read_all(limit=limit)]


@router.post("/", status_code=201)
def file_verdict(
    req: VerdictRequest,
    store: VerdictStoreDep = Depends(get_verdict_store),  # type: ignore[assignment]
) -> dict:
    import uuid
    from cls_verdicts.schemas import Verdict, VALID_OUTCOMES

    if req.outcome not in VALID_OUTCOMES:
        raise HTTPException(status_code=422, detail=f"outcome must be one of {sorted(VALID_OUTCOMES)}")

    verdict = Verdict(
        verdict_id=str(uuid.uuid4()),
        record_id=req.record_id,
        outcome=req.outcome,
        analyst_id=req.analyst_id,
        notes=req.notes,
    )
    store.append(verdict)
    return verdict.to_dict()
