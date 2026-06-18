# @domain:   intelligence
# @module:   adapters_pdx911
# @loc:      gh_main
# @status:   stable
# @depends:  cls_db, spec1_core

"""Portland 911 incidents adapter.

Fetches the live KML feed from PortlandMaps and parses it into Pdx911Record instances.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Iterator, Optional, Tuple

import requests

from cls_osint.schemas import OSINTRecord, Pdx911Record

FEED_URL = "https://www.portlandmaps.com/scripts/911incidents-kml_link.cfm"
TIMEOUT = 15
_KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}

_HEADERS = {
    "User-Agent": "spec1-engine/0.3 (research; contact: research@spec1.io)",
}

_TIMESTAMP_RE = re.compile(
    r"[A-Za-z]+,\s[A-Za-z]+\s\d+,\s\d{4}\s\d+:\d+\s[A-Z]{2}"
)
_CASE_RE = re.compile(r"\[(.*?) Police #(.*?)\]")


def _parse_timestamp(desc: str) -> Optional[datetime]:
    m = _TIMESTAMP_RE.search(desc)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(0), "%A, %B %d, %Y %I:%M %p")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_agency_case(desc: str) -> Tuple[str, Optional[str]]:
    m = _CASE_RE.search(desc)
    if m:
        return f"{m.group(1)} Police", m.group(2)
    return "Unknown Agency", None


def _parse_coords(coord_el) -> Tuple[Optional[float], Optional[float]]:
    if coord_el is None or not coord_el.text:
        return None, None
    parts = [c.strip() for c in coord_el.text.strip().split(",")]
    if len(parts) < 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None, None


def fetch_incidents(url: str = FEED_URL, timeout: int = TIMEOUT) -> list[Pdx911Record]:
    """Fetch and parse the Portland 911 KML feed. Returns [] on parse error."""
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return []

    records: list[Pdx911Record] = []
    for placemark in root.findall(".//kml:Placemark", _KML_NS):
        raw_title = placemark.find("kml:name", _KML_NS)
        raw_desc = placemark.find("kml:description", _KML_NS)
        coord_el = placemark.find(".//kml:coordinates", _KML_NS)

        title = raw_title.text.strip() if raw_title is not None else "UNKNOWN"
        desc = raw_desc.text.strip() if raw_desc is not None else ""

        incident_type = "UNKNOWN"
        location = "UNKNOWN"
        if " at " in title:
            left, right = title.split(" at ", 1)
            incident_type = left.strip()
            location = right.replace(", PORT", "").replace(", GRSM", "").strip()

        agency, case_id = _parse_agency_case(desc)
        timestamp = _parse_timestamp(desc)
        longitude, latitude = _parse_coords(coord_el)

        records.append(
            Pdx911Record(
                record_id=Pdx911Record.make_id(case_id, incident_type, location),
                case_id=case_id,
                agency=agency,
                incident_type=incident_type,
                location_block=location,
                timestamp=timestamp,
                longitude=longitude,
                latitude=latitude,
                metadata={"source_title": title, "raw_desc": desc[:500]},
            )
        )

    return records


def collect(timeout: int = TIMEOUT) -> list[Pdx911Record]:
    """Main entry point — returns [] on any network or parse failure."""
    try:
        return fetch_incidents(timeout=timeout)
    except Exception:
        return []


def iter_records(timeout: int = TIMEOUT) -> Iterator[OSINTRecord]:
    """Yield OSINTRecord instances from the live Portland 911 feed."""
    for record in collect(timeout=timeout):
        yield record.to_osint_record()
