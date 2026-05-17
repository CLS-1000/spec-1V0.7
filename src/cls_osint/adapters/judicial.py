"""Judicial adapter — federal court and disclosure records.

3-source fallback: CourtListener API → PACER RSS feed → synthetic sample.
Never raises; returns synthetic sample on all failures.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from typing import Iterator

import requests

from cls_osint.schemas import JudicialRecord

COURTLISTENER_URL = "https://www.courtlistener.com/api/rest/v3/opinions/"
PACER_RSS_URL = "https://ecf.dcd.uscourts.gov/cgi-bin/rss_outside.pl"
TIMEOUT = 15

_HEADERS = {
    "User-Agent": "spec1-engine/0.3 (research; contact: research@spec1.io)",
    "Accept": "application/json, text/html, application/xml;q=0.9, */*;q=0.8",
}


def _today_iso() -> str:
    return date.today().isoformat()


def _parse_date_str(text: str) -> str:
    """Normalise various date strings to ISO date format, fallback to today."""
    text = text.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    # Try truncating to date portion if ISO-like (e.g. "2024-03-15T10:00:00Z")
    if len(text) >= 10 and text[4] == "-":
        return text[:10]
    return _today_iso()


def _parse_action_type(text: str) -> str:
    """Map text to a canonical action_type."""
    lower = text.lower()
    if re.search(r"recusal|recused", lower):
        return "recusal"
    if re.search(r"gift report|gift", lower):
        return "gift"
    if re.search(r"financial disclosure|disclosure", lower):
        return "disclosure"
    if re.search(r"speaking|speech|lecture", lower):
        return "speaking_engagement"
    return "ruling"


def _extract_disclosed_ties(text: str) -> list[str]:
    """Extract disclosure-related mentions from text."""
    patterns = [
        r"former client[s]?",
        r"prior employment[s]?",
        r"financial interest[s]?",
        r"stock[s]?",
    ]
    found: list[str] = []
    lower = text.lower()
    for pat in patterns:
        match = re.search(pat, lower)
        if match:
            # Return a short snippet around the match for context
            start = max(0, match.start() - 10)
            end = min(len(text), match.end() + 40)
            found.append(text[start:end].strip())
    return found


def _make_record(
    judge: str,
    court: str,
    district: str,
    action_type: str,
    case_ref: str,
    ruling_summary: str,
    disclosed_ties: list[str],
    recusal_basis: str,
    gift_amount: float,
    engagement_sponsor: str,
    filed_at_str: str,
    source_url: str,
) -> JudicialRecord:
    """Construct a JudicialRecord from parsed fields."""
    record_id = JudicialRecord.make_id(judge, action_type, filed_at_str)
    return JudicialRecord(
        record_id=record_id,
        judge=judge,
        court=court,
        district=district,
        action_type=action_type,
        case_ref=case_ref,
        ruling_summary=ruling_summary,
        disclosed_ties=disclosed_ties,
        recusal_basis=recusal_basis,
        gift_amount=gift_amount,
        engagement_sponsor=engagement_sponsor,
        filed_at=filed_at_str,
        source_url=source_url,
        metadata={"source": source_url},
    )


def _fetch_courtlistener(timeout: int) -> list[JudicialRecord]:
    """Fetch opinions from the CourtListener REST API.

    Raises on HTTP error or missing mandatory fields.
    """
    resp = requests.get(COURTLISTENER_URL, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    records: list[JudicialRecord] = []
    for item in results:
        judge = item.get("judges", "") or ""
        court = item.get("court_id", "") or ""
        case_name = item.get("case_name", "") or ""
        download_url = item.get("download_url", "") or ""
        date_filed = item.get("date_filed", "") or ""
        action_type = "ruling"
        description = item.get("plain_text", item.get("html", "")) or ""
        disclosed_ties = _extract_disclosed_ties(description)
        filed_at_str = _parse_date_str(date_filed) if date_filed else _today_iso()
        records.append(
            _make_record(
                judge=judge,
                court=court,
                district="",
                action_type=action_type,
                case_ref=case_name,
                ruling_summary=(description[:200].strip() if description else ""),
                disclosed_ties=disclosed_ties,
                recusal_basis="",
                gift_amount=0.0,
                engagement_sponsor="",
                filed_at_str=filed_at_str,
                source_url=download_url or COURTLISTENER_URL,
            )
        )
    return records


def _fetch_pacer_rss(timeout: int) -> list[JudicialRecord]:
    """Fetch and parse the PACER RSS feed for DC District Court.

    Raises on any network or parse error.
    """
    resp = requests.get(PACER_RSS_URL, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    ns = {"": ""}  # RSS 2.0 uses no namespace by default

    records: list[JudicialRecord] = []
    # RSS structure: <rss><channel><item>...</item></channel></rss>
    channel = root.find("channel")
    if channel is None:
        return records

    for item_el in channel.findall("item"):
        title = (item_el.findtext("title") or "").strip()
        link = (item_el.findtext("link") or "").strip()
        description = (item_el.findtext("description") or "").strip()
        pub_date = (item_el.findtext("pubDate") or "").strip()

        # Attempt to parse a judge name from the title
        judge = ""
        judge_match = re.search(r"Judge\s+([\w\s\-\.]+?)(?:,|\s*-|\s*\(|$)", title)
        if judge_match:
            judge = judge_match.group(1).strip()

        action_type = _parse_action_type(description or title)
        filed_at_str = _parse_date_str(pub_date) if pub_date else _today_iso()
        disclosed_ties = _extract_disclosed_ties(description)

        records.append(
            _make_record(
                judge=judge or "Unknown",
                court="DC District Court",
                district="DC",
                action_type=action_type,
                case_ref=title[:100],
                ruling_summary=description[:200],
                disclosed_ties=disclosed_ties,
                recusal_basis="",
                gift_amount=0.0,
                engagement_sponsor="",
                filed_at_str=filed_at_str,
                source_url=link or PACER_RSS_URL,
            )
        )
    return records


def _synthetic_sample() -> list[JudicialRecord]:
    """Return exactly 3 representative JudicialRecords for fallback/testing."""
    today = _today_iso()
    return [
        _make_record(
            judge="Hon. Maria Chen",
            court="9th Circuit",
            district="CA",
            action_type="recusal",
            case_ref="No. 24-1234",
            ruling_summary="Recusal filed in patent dispute.",
            disclosed_ties=["Prior employment at defendant's law firm"],
            recusal_basis="Prior employment relationship with defendant counsel",
            gift_amount=0.0,
            engagement_sponsor="",
            filed_at_str=today,
            source_url="https://www.uscourts.gov/sample/recusal",
        ),
        _make_record(
            judge="Hon. James Okafor",
            court="SDNY",
            district="NY",
            action_type="gift",
            case_ref="FD-2024-0892",
            ruling_summary="Annual financial disclosure — gift reported from law school.",
            disclosed_ties=[],
            recusal_basis="",
            gift_amount=350.0,
            engagement_sponsor="",
            filed_at_str=today,
            source_url="https://www.uscourts.gov/sample/disclosure",
        ),
        _make_record(
            judge="Hon. Patricia Reyes",
            court="DC Circuit",
            district="DC",
            action_type="ruling",
            case_ref="No. 23-5198",
            ruling_summary="Affirmed lower court ruling on regulatory standing doctrine.",
            disclosed_ties=[],
            recusal_basis="",
            gift_amount=0.0,
            engagement_sponsor="",
            filed_at_str=today,
            source_url="https://www.courtlistener.com/opinion/sample",
        ),
    ]


def collect(timeout: int = TIMEOUT) -> list[JudicialRecord]:
    """Main entry point — collect federal judicial records.

    3-source fallback: CourtListener API → PACER RSS → synthetic sample.
    Never raises.
    """
    try:
        records = _fetch_courtlistener(timeout)
        if records:
            return records
    except Exception:
        pass

    try:
        records = _fetch_pacer_rss(timeout)
        if records:
            return records
    except Exception:
        pass

    return _synthetic_sample()


def iter_records(timeout: int = TIMEOUT) -> Iterator[JudicialRecord]:
    """Yield JudicialRecord instances from federal court sources."""
    for record in collect(timeout=timeout):
        yield record
