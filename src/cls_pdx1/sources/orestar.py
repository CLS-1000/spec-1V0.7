"""ORESTAR adapter — Oregon SOS campaign finance.

Production path: Oregon Secretary of State ORESTAR bulk CSV export.
Export URL: https://sos.oregon.gov/elections/Pages/orestar.aspx
CSV columns (as of 2025): filer_id, filer_name, transaction_type, amount,
    contributor_name, contributor_address, transaction_date, election_year

HTTP scrape is stubbed — raises NotImplementedError so pipeline.run_cycle
catches it and logs the gap rather than crashing.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from cls_pdx1.models import Affiliation, ConfidenceTier, EdgeType, Provenance
from cls_pdx1.sources.base import AdapterResult, BaseAdapter

logger = logging.getLogger(__name__)

_SOURCE_URI_BASE = "https://sos.oregon.gov/elections/Pages/orestar.aspx"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_row(row: dict, fetched_at: datetime) -> Optional[Affiliation]:
    """Parse a single ORESTAR CSV row into an Affiliation edge."""
    try:
        amount_str = row.get("amount", "0").replace("$", "").replace(",", "").strip()
        amount = float(amount_str) if amount_str else 0.0
        txn_date_str = row.get("transaction_date", "")
        try:
            txn_date = datetime.strptime(txn_date_str, "%m/%d/%Y").date()
        except ValueError:
            txn_date = fetched_at.date()

        filer_name = row.get("filer_name", "").strip()
        contributor_name = row.get("contributor_name", "").strip()
        if not filer_name or not contributor_name:
            return None

        from cls_pdx1.models import Jurisdiction, _make_id

        official_id = _make_id("official", filer_name, "candidate", str(int(Jurisdiction.STATE_OREGON)))
        entity_id = _make_id("entity", contributor_name)

        return Affiliation(
            official_id=official_id,
            entity_id=entity_id,
            edge_type=EdgeType.DONATION,
            confidence=ConfidenceTier.HARD_RECORD,
            observed_at=fetched_at,
            valid_from=txn_date,
            amount=amount,
            description=f"ORESTAR: {contributor_name} → {filer_name} (${amount:,.2f})",
            provenance=Provenance(
                source_uri=_SOURCE_URI_BASE,
                source_name="ORESTAR",
                fetched_at=fetched_at,
            ),
        )
    except Exception as exc:
        logger.debug("ORESTAR row parse error: %s — row: %s", exc, row)
        return None


class OrestarAdapter(BaseAdapter):
    """Parses ORESTAR campaign finance records from a local CSV export."""

    source_name = "ORESTAR"

    def __init__(self, csv_path: Optional[Union[str, Path]] = None) -> None:
        self._csv_path = Path(csv_path) if csv_path else None

    def fetch(self) -> AdapterResult:
        if self._csv_path is None:
            return AdapterResult(
                source_name=self.source_name,
                errors=["ORESTAR HTTP scrape not implemented — provide csv_path"],
            )

        if not self._csv_path.exists():
            return AdapterResult(
                source_name=self.source_name,
                errors=[f"CSV not found: {self._csv_path}"],
            )

        fetched_at = _now()
        records: list[Affiliation] = []
        errors: list[str] = []

        try:
            with self._csv_path.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    aff = _parse_row(row, fetched_at)
                    if aff:
                        records.append(aff)
        except Exception as exc:
            errors.append(f"ORESTAR CSV read error: {exc}")

        logger.info("ORESTAR: parsed %d affiliations, %d errors", len(records), len(errors))
        return AdapterResult(records=records, errors=errors, source_name=self.source_name)

    def fetch_from_csv_text(self, csv_text: str) -> AdapterResult:
        """Parse from in-memory CSV text (for testing)."""
        fetched_at = _now()
        records: list[Affiliation] = []
        errors: list[str] = []
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            for row in reader:
                aff = _parse_row(row, fetched_at)
                if aff:
                    records.append(aff)
        except Exception as exc:
            errors.append(f"CSV parse error: {exc}")
        return AdapterResult(records=records, errors=errors, source_name=self.source_name)
