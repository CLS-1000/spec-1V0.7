"""OLIS adapter — Oregon Legislative Information System.

Tracks bills, votes, committee membership, and hearing witnesses.
OLIS OData API: https://api.oregonlegislature.gov/odata/odataservice.svc/

HTTP fetch is fully stubbed to avoid network dependency in tests.
Provide bill_data list directly via OlisAdapter(bill_data=[...]) for testing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from cls_pdx1.models import Bill, BillStatus, Jurisdiction, Provenance, _make_id
from cls_pdx1.sources.base import AdapterResult, BaseAdapter

logger = logging.getLogger(__name__)

_OLIS_BASE = "https://api.oregonlegislature.gov/odata/odataservice.svc/"
_SOURCE_URI = "https://www.oregonlegislature.gov/"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _map_status(raw: str) -> BillStatus:
    raw_lower = raw.lower()
    # Check longest matches first to avoid substring ambiguity
    if "passed both chambers" in raw_lower or "enrolled" in raw_lower:
        return BillStatus.PASSED_BOTH_CHAMBERS
    if "signed" in raw_lower:
        return BillStatus.SIGNED
    if "vetoed" in raw_lower:
        return BillStatus.VETOED
    if "overridden" in raw_lower:
        return BillStatus.OVERRIDDEN
    if "passed committee" in raw_lower:
        return BillStatus.PASSED_COMMITTEE
    if "passed" in raw_lower:
        return BillStatus.PASSED_ONE_CHAMBER
    if "committee" in raw_lower:
        return BillStatus.IN_COMMITTEE
    if "failed" in raw_lower:
        return BillStatus.FAILED
    if "dead" in raw_lower or "pocket" in raw_lower:
        return BillStatus.DEAD
    return BillStatus.INTRODUCED


def _parse_bill(raw: dict[str, Any], fetched_at: datetime) -> Optional[Bill]:
    try:
        external_id = raw.get("MeasureNumber", raw.get("bill_id", ""))
        title = raw.get("RelatingClause", raw.get("title", ""))
        status_raw = raw.get("CurrentStatus", raw.get("status", "introduced"))
        sponsor = raw.get("ChiefSponsor", raw.get("sponsor", ""))
        source_url = raw.get("source_url", _SOURCE_URI)

        if not external_id:
            return None

        bill_id = _make_id("bill", str(int(Jurisdiction.STATE_OREGON)), external_id)
        return Bill(
            bill_id=bill_id,
            external_id=external_id,
            title=title or external_id,
            jurisdiction=Jurisdiction.STATE_OREGON,
            chamber=raw.get("Chamber", raw.get("chamber", "Unknown")),
            sponsor=sponsor or None,
            status=_map_status(status_raw),
            source_url=source_url,
            tags=raw.get("tags", []),
            provenance=Provenance(
                source_uri=source_url if source_url.startswith("http") else _SOURCE_URI,
                source_name="OLIS",
                fetched_at=fetched_at,
            ),
        )
    except Exception as exc:
        logger.debug("OLIS bill parse error: %s", exc)
        return None


class OlisAdapter(BaseAdapter):
    """Returns Bill records from OLIS. Accepts pre-loaded data for testing."""

    source_name = "OLIS"

    def __init__(self, bill_data: Optional[list[dict]] = None) -> None:
        self._bill_data = bill_data

    def fetch(self) -> AdapterResult:
        if self._bill_data is not None:
            return self._parse_data(self._bill_data)

        # HTTP fetch not implemented — pipeline catches and logs
        return AdapterResult(
            source_name=self.source_name,
            errors=["OLIS HTTP fetch not implemented — provide bill_data list"],
        )

    def _parse_data(self, data: list[dict]) -> AdapterResult:
        fetched_at = _now()
        records: list[Bill] = []
        errors: list[str] = []
        for raw in data:
            bill = _parse_bill(raw, fetched_at)
            if bill:
                records.append(bill)
            else:
                errors.append(f"failed to parse: {raw.get('MeasureNumber', raw.get('bill_id', '?'))}")
        logger.info("OLIS: parsed %d bills, %d errors", len(records), len(errors))
        return AdapterResult(records=records, errors=errors, source_name=self.source_name)
