# @domain:   intelligence
# @module:   adapters_state_legislative
# @loc:      gh_main
# @status:   stable
# @depends:  cls_db, spec1_core

"""State legislative adapter.

3-source fallback: OpenStates API → LegiScan API → synthetic sample.
Tracks per-state disclosure regime coverage.
Never raises; returns synthetic sample on all failures.
"""

from __future__ import annotations

import os
import re
from datetime import date
from typing import Iterator

import requests

from cls_osint.schemas import StateLegRecord

OPENSTATES_URL = "https://v3.openstates.org/bills"
LEGISCAN_URL = "https://api.legiscan.com/"
TIMEOUT = 15

# Per-state disclosure regime: FULL = comprehensive lobbying+financial disclosure,
# PARTIAL = some disclosure required, NONE = no mandatory disclosure
STATE_DISCLOSURE_REGIMES: dict[str, str] = {
    "AK": "FULL", "AL": "PARTIAL", "AR": "PARTIAL", "AZ": "PARTIAL",
    "CA": "FULL", "CO": "FULL", "CT": "FULL", "DE": "PARTIAL",
    "FL": "FULL", "GA": "PARTIAL", "HI": "FULL", "IA": "PARTIAL",
    "ID": "NONE", "IL": "FULL", "IN": "PARTIAL", "KS": "NONE",
    "KY": "PARTIAL", "LA": "PARTIAL", "MA": "FULL", "MD": "FULL",
    "ME": "FULL", "MI": "PARTIAL", "MN": "FULL", "MO": "NONE",
    "MS": "NONE", "MT": "PARTIAL", "NC": "PARTIAL", "ND": "NONE",
    "NE": "PARTIAL", "NH": "PARTIAL", "NJ": "FULL", "NM": "PARTIAL",
    "NV": "PARTIAL", "NY": "FULL", "OH": "PARTIAL", "OK": "NONE",
    "OR": "FULL", "PA": "PARTIAL", "RI": "PARTIAL", "SC": "NONE",
    "SD": "NONE", "TN": "NONE", "TX": "PARTIAL", "UT": "PARTIAL",
    "VA": "FULL", "VT": "FULL", "WA": "FULL", "WI": "PARTIAL",
    "WV": "NONE", "WY": "NONE",
}

_HEADERS = {
    "User-Agent": "spec1-engine/0.3 (research; contact: research@spec1.io)",
    "Accept": "application/json",
}


def _today_iso() -> str:
    return date.today().isoformat()


def _classify_status(text: str) -> str:
    """Map an action description to a canonical status."""
    lower = text.lower()
    if re.search(r"enacted|signed", lower):
        return "ENACTED"
    if re.search(r"passed\b.*\bsenate|senate\b.*\bpassed", lower):
        return "PASSED_SENATE"
    if re.search(r"passed\b.*\bhouse|house\b.*\bpassed", lower):
        return "PASSED_HOUSE"
    if re.search(r"failed|vetoed", lower):
        return "FAILED"
    return "INTRODUCED"


def _classify_chamber(bill_id: str, text: str) -> str:
    """Determine chamber from bill identifier prefix."""
    upper = bill_id.upper()
    if re.match(r"(SB|SR|SCR)\b", upper):
        return "SENATE"
    if re.match(r"(HB|HR|HCR)\b", upper):
        return "HOUSE"
    return "JOINT"


def _get_disclosure_regime(state: str) -> tuple[str, bool]:
    """Return (regime, has_gap) for a state.

    has_gap is True when the regime is NONE, PARTIAL, or the state is unknown.
    """
    regime = STATE_DISCLOSURE_REGIMES.get(state.upper())
    if regime is None:
        return ("NONE", True)
    has_gap = regime in ("NONE", "PARTIAL")
    return (regime, has_gap)


def _fetch_openstates(timeout: int, states: list[str] | None) -> list[StateLegRecord]:
    """Fetch bills from the OpenStates v3 API.

    Raises on HTTP error or missing key.
    """
    params: dict[str, object] = {
        "apikey": os.environ.get("OPENSTATES_API_KEY", ""),
        "per_page": 20,
    }
    if states:
        params["jurisdiction"] = ",".join(s.lower() for s in states)

    resp = requests.get(OPENSTATES_URL, params=params, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    results = data["results"]  # Raise KeyError on missing key

    records: list[StateLegRecord] = []
    for item in results:
        bill_id: str = item["identifier"]
        title: str = item.get("title", "")
        latest_action: str = item.get("latest_action_description", "")
        status = _classify_status(latest_action)
        chamber = _classify_chamber(bill_id, title)

        # Derive state from jurisdiction slug (e.g. "ocd-jurisdiction/country:us/state:ca/...")
        jurisdiction = item.get("jurisdiction", {})
        state_raw = ""
        if isinstance(jurisdiction, dict):
            jid = jurisdiction.get("id", "")
            match = re.search(r"state:([a-z]{2})", jid)
            state_raw = match.group(1).upper() if match else jurisdiction.get("name", "")[:2].upper()
        elif isinstance(jurisdiction, str):
            match = re.search(r"state:([a-z]{2})", jurisdiction)
            state_raw = match.group(1).upper() if match else jurisdiction[:2].upper()

        sponsorships = item.get("sponsorships", [])
        sponsor = sponsorships[0]["name"] if sponsorships else ""

        regime, gap = _get_disclosure_regime(state_raw)
        filed_at = _today_iso()

        record_id = StateLegRecord.make_id(state_raw, bill_id, filed_at)
        records.append(
            StateLegRecord(
                record_id=record_id,
                state=state_raw,
                bill_id=bill_id,
                title=title,
                sponsor=sponsor,
                chamber=chamber,
                status=status,
                summary=latest_action[:300],
                disclosure_regime=regime,
                disclosure_gap=gap,
                filed_at=filed_at,
                source_url=item.get("openstates_url", OPENSTATES_URL),
                tags=[],
                metadata={"source": "openstates"},
            )
        )
    return records


def _fetch_legiscan(timeout: int, states: list[str] | None) -> list[StateLegRecord]:
    """Fetch session list from the LegiScan API.

    Raises on HTTP error or API-level error.
    """
    params: dict[str, str] = {
        "key": os.environ.get("LEGISCAN_API_KEY", ""),
        "op": "getSessionList",
        "state": "US",
    }
    resp = requests.get(LEGISCAN_URL, params=params, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") == "ERROR":
        raise ValueError(f"LegiScan API error: {data.get('alert', {}).get('message', 'unknown')}")

    sessions = data.get("sessions", [])
    records: list[StateLegRecord] = []
    for session in sessions[:20]:
        state_abbr: str = session.get("state_abbr", "") or ""
        if states and state_abbr.upper() not in [s.upper() for s in states]:
            continue
        session_name: str = session.get("session_name", "") or ""
        regime, gap = _get_disclosure_regime(state_abbr)
        filed_at = _today_iso()
        bill_id = f"{state_abbr} SESSION-{session.get('session_id', '')}"
        record_id = StateLegRecord.make_id(state_abbr, bill_id, filed_at)
        records.append(
            StateLegRecord(
                record_id=record_id,
                state=state_abbr,
                bill_id=bill_id,
                title=session_name,
                sponsor="",
                chamber="JOINT",
                status="INTRODUCED",
                summary=f"Legislative session: {session_name}",
                disclosure_regime=regime,
                disclosure_gap=gap,
                filed_at=filed_at,
                source_url=LEGISCAN_URL,
                tags=[],
                metadata={"source": "legiscan", "session": session},
            )
        )
    return records


def _synthetic_sample() -> list[StateLegRecord]:
    """Return exactly 3 representative StateLegRecords for fallback/testing."""
    today = _today_iso()
    return [
        StateLegRecord(
            record_id=StateLegRecord.make_id("CA", "CA SB 1442", today),
            state="CA",
            bill_id="CA SB 1442",
            title="Digital Transparency in Lobbying Act",
            sponsor="Sen. Michelle Park Steel",
            chamber="SENATE",
            status="INTRODUCED",
            summary="Requires real-time disclosure of digital lobbying contacts to state agencies.",
            disclosure_regime="FULL",
            disclosure_gap=False,
            filed_at=today,
            source_url="https://leginfo.legislature.ca.gov/sample",
            tags=["lobbying", "transparency", "digital"],
            metadata={"source": "synthetic"},
        ),
        StateLegRecord(
            record_id=StateLegRecord.make_id("TX", "TX HB 2891", today),
            state="TX",
            bill_id="TX HB 2891",
            title="Energy Infrastructure Regulatory Reform Act",
            sponsor="Rep. Tom Harmon",
            chamber="HOUSE",
            status="PASSED_HOUSE",
            summary="Reduces PUCT review timelines for natural gas infrastructure permits.",
            disclosure_regime="PARTIAL",
            disclosure_gap=True,
            filed_at=today,
            source_url="https://capitol.texas.gov/sample",
            tags=["energy", "regulation", "infrastructure"],
            metadata={"source": "synthetic"},
        ),
        StateLegRecord(
            record_id=StateLegRecord.make_id("WY", "WY HB 0044", today),
            state="WY",
            bill_id="WY HB 0044",
            title="Agricultural Exemption Expansion Act",
            sponsor="Rep. Clark Stith",
            chamber="HOUSE",
            status="ENACTED",
            summary="Expands sales tax exemptions for agricultural equipment purchases.",
            disclosure_regime="NONE",
            disclosure_gap=True,
            filed_at=today,
            source_url="https://www.wyoleg.gov/sample",
            tags=["agriculture", "tax", "exemption"],
            metadata={"source": "synthetic"},
        ),
    ]


def collect(
    timeout: int = TIMEOUT,
    states: list[str] | None = None,
) -> list[StateLegRecord]:
    """Main entry point — collect state legislative records.

    3-source fallback: OpenStates API → LegiScan API → synthetic sample.
    Never raises.
    """
    try:
        records = _fetch_openstates(timeout, states)
        if records:
            return records
    except Exception:
        pass

    try:
        records = _fetch_legiscan(timeout, states)
        if records:
            return records
    except Exception:
        pass

    return _synthetic_sample()


def iter_records(timeout: int = TIMEOUT) -> Iterator[StateLegRecord]:
    """Yield StateLegRecord instances from state legislature sources."""
    for record in collect(timeout=timeout):
        yield record
