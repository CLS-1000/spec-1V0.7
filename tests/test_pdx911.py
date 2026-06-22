# @domain:   intelligence
# @module:   test_pdx911
# @loc:      gh_main
# @status:   testing
# @depends:  NONE

"""Tests for cls_osint.adapters.pdx911 — Portland 911 KML feed adapter."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cls_osint.adapters.pdx911 import (
    _parse_agency_case,
    _parse_coords,
    _parse_timestamp,
    collect,
    fetch_incidents,
    iter_records,
)
from cls_osint.schemas import OSINTRecord, Pdx911Record


# ── KML fixture helpers ────────────────────────────────────────────────────────

_KML_WRAPPER = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    {placemarks}
  </Document>
</kml>"""

_PLACEMARK_TEMPLATE = """\
<Placemark xmlns="http://www.opengis.net/kml/2.2">
  <name>{title}</name>
  <description>{desc}</description>
  <Point>
    <coordinates>{lon},{lat},0</coordinates>
  </Point>
</Placemark>"""


def _make_kml(placemarks: list[str]) -> bytes:
    return _KML_WRAPPER.format(placemarks="\n".join(placemarks)).encode()


def _make_placemark(
    title: str = "UNWANTED PERSON at 1900 SE 6TH AVE, PORT",
    desc: str = "Thursday, June 20, 2024 10:30 AM [Portland Police #PP24001234]",
    lon: float = -122.6584,
    lat: float = 45.5051,
) -> str:
    return _PLACEMARK_TEMPLATE.format(title=title, desc=desc, lon=lon, lat=lat)


def _mock_response(content: bytes, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


# ── _parse_timestamp ───────────────────────────────────────────────────────────

class TestParseTimestamp:
    def test_valid_timestamp_returns_datetime(self):
        desc = "Thursday, June 20, 2024 10:30 AM [Portland Police #PP24001234]"
        result = _parse_timestamp(desc)
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 20
        assert result.hour == 10
        assert result.minute == 30

    def test_returned_datetime_is_utc_aware(self):
        desc = "Monday, January 01, 2024 08:00 AM [Portland Police #PP24000001]"
        result = _parse_timestamp(desc)
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_pm_time_parses_correctly(self):
        desc = "Friday, March 15, 2024 03:45 PM [Portland Police #PP24005000]"
        result = _parse_timestamp(desc)
        assert result is not None
        assert result.hour == 15
        assert result.minute == 45

    def test_no_timestamp_returns_none(self):
        desc = "No timestamp in this description"
        assert _parse_timestamp(desc) is None

    def test_empty_string_returns_none(self):
        assert _parse_timestamp("") is None

    def test_partial_timestamp_returns_none(self):
        # A string that partially resembles a timestamp but won't match the full regex
        assert _parse_timestamp("June 20, 2024") is None


# ── _parse_agency_case ─────────────────────────────────────────────────────────

class TestParseAgencyCase:
    def test_extracts_agency_and_case_id(self):
        desc = "Thursday, June 20, 2024 10:30 AM [Portland Police #PP24001234]"
        agency, case_id = _parse_agency_case(desc)
        assert agency == "Portland Police"
        assert case_id == "PP24001234"

    def test_different_agency_name(self):
        desc = "Monday, June 17, 2024 09:00 AM [Gresham Police #GR24000099]"
        agency, case_id = _parse_agency_case(desc)
        assert agency == "Gresham Police"
        assert case_id == "GR24000099"

    def test_no_match_returns_unknown_and_none(self):
        desc = "No agency info here"
        agency, case_id = _parse_agency_case(desc)
        assert agency == "Unknown Agency"
        assert case_id is None

    def test_empty_string_returns_defaults(self):
        agency, case_id = _parse_agency_case("")
        assert agency == "Unknown Agency"
        assert case_id is None

    def test_case_id_preserved_exactly(self):
        desc = "[Multnomah County Police #MC26999999]"
        _, case_id = _parse_agency_case(desc)
        assert case_id == "MC26999999"


# ── _parse_coords ──────────────────────────────────────────────────────────────

class TestParseCoords:
    def _make_coord_el(self, text: str) -> ET.Element:
        el = ET.Element("coordinates")
        el.text = text
        return el

    def test_valid_lon_lat_returns_floats(self):
        el = self._make_coord_el("-122.6584,45.5051,0")
        lon, lat = _parse_coords(el)
        assert abs(lon - (-122.6584)) < 1e-4
        assert abs(lat - 45.5051) < 1e-4

    def test_returns_lon_then_lat_order(self):
        el = self._make_coord_el("-123.0,45.0,0")
        lon, lat = _parse_coords(el)
        assert lon == -123.0
        assert lat == 45.0

    def test_none_element_returns_none_tuple(self):
        assert _parse_coords(None) == (None, None)

    def test_empty_text_returns_none_tuple(self):
        el = ET.Element("coordinates")
        el.text = ""
        assert _parse_coords(el) == (None, None)

    def test_single_value_returns_none_tuple(self):
        el = self._make_coord_el("-122.6584")
        assert _parse_coords(el) == (None, None)

    def test_non_float_values_returns_none_tuple(self):
        el = self._make_coord_el("not,a,number")
        assert _parse_coords(el) == (None, None)

    def test_whitespace_stripped(self):
        el = self._make_coord_el("  -122.6584 , 45.5051 , 0  ")
        lon, lat = _parse_coords(el)
        assert lon is not None
        assert lat is not None


# ── fetch_incidents ────────────────────────────────────────────────────────────

class TestFetchIncidents:
    def test_parses_single_placemark(self):
        kml = _make_kml([_make_placemark()])
        with patch("requests.get", return_value=_mock_response(kml)):
            records = fetch_incidents()

        assert len(records) == 1
        r = records[0]
        assert isinstance(r, Pdx911Record)
        assert r.incident_type == "UNWANTED PERSON"
        assert r.location_block == "1900 SE 6TH AVE"
        assert r.agency == "Portland Police"
        assert r.case_id == "PP24001234"
        assert r.longitude is not None
        assert r.latitude is not None

    def test_parses_multiple_placemarks(self):
        p1 = _make_placemark(
            title="THEFT at 100 NW BROADWAY, PORT",
            desc="Thursday, June 20, 2024 08:00 AM [Portland Police #PP24000001]",
            lon=-122.6784,
            lat=45.5231,
        )
        p2 = _make_placemark(
            title="ASSAULT at 500 SW 3RD AVE, PORT",
            desc="Thursday, June 20, 2024 09:00 AM [Portland Police #PP24000002]",
            lon=-122.6715,
            lat=45.5182,
        )
        kml = _make_kml([p1, p2])
        with patch("requests.get", return_value=_mock_response(kml)):
            records = fetch_incidents()

        assert len(records) == 2
        types = {r.incident_type for r in records}
        assert "THEFT" in types
        assert "ASSAULT" in types

    def test_strips_port_suffix_from_location(self):
        kml = _make_kml([_make_placemark(title="FIGHT at 200 NE MLK BLVD, PORT")])
        with patch("requests.get", return_value=_mock_response(kml)):
            records = fetch_incidents()

        assert records[0].location_block == "200 NE MLK BLVD"

    def test_strips_grsm_suffix_from_location(self):
        kml = _make_kml([_make_placemark(title="NOISE at 400 SE STARK ST, GRSM")])
        with patch("requests.get", return_value=_mock_response(kml)):
            records = fetch_incidents()

        assert records[0].location_block == "400 SE STARK ST"

    def test_title_without_at_separator_sets_unknown(self):
        kml = _make_kml([_make_placemark(title="UNKNOWN INCIDENT")])
        with patch("requests.get", return_value=_mock_response(kml)):
            records = fetch_incidents()

        assert records[0].incident_type == "UNKNOWN"
        assert records[0].location_block == "UNKNOWN"

    def test_returns_empty_on_malformed_xml(self):
        bad_xml = b"<not valid xml <<<"
        with patch("requests.get", return_value=_mock_response(bad_xml)):
            records = fetch_incidents()

        assert records == []

    def test_raises_on_http_error(self):
        with patch("requests.get", return_value=_mock_response(b"", status_code=503)):
            with pytest.raises(Exception):
                fetch_incidents()

    def test_record_id_is_deterministic(self):
        kml = _make_kml([_make_placemark()])
        with patch("requests.get", return_value=_mock_response(kml)):
            r1 = fetch_incidents()
        with patch("requests.get", return_value=_mock_response(kml)):
            r2 = fetch_incidents()

        assert r1[0].record_id == r2[0].record_id

    def test_metadata_contains_source_title(self):
        kml = _make_kml([_make_placemark(title="FIGHT at 300 SE DIVISION ST, PORT")])
        with patch("requests.get", return_value=_mock_response(kml)):
            records = fetch_incidents()

        assert "source_title" in records[0].metadata
        assert records[0].metadata["source_title"] == "FIGHT at 300 SE DIVISION ST, PORT"

    def test_empty_kml_returns_empty_list(self):
        kml = _make_kml([])
        with patch("requests.get", return_value=_mock_response(kml)):
            records = fetch_incidents()

        assert records == []


# ── collect ────────────────────────────────────────────────────────────────────

class TestCollect:
    def test_returns_records_on_success(self):
        kml = _make_kml([_make_placemark()])
        with patch("requests.get", return_value=_mock_response(kml)):
            records = collect()

        assert len(records) == 1

    def test_returns_empty_list_on_network_error(self):
        with patch("requests.get", side_effect=ConnectionError("network down")):
            records = collect()

        assert records == []

    def test_returns_empty_list_on_http_error(self):
        with patch("requests.get", return_value=_mock_response(b"", status_code=500)):
            records = collect()

        assert records == []

    def test_returns_empty_list_on_timeout(self):
        import requests as req
        with patch("requests.get", side_effect=req.Timeout("timed out")):
            records = collect()

        assert records == []


# ── iter_records ───────────────────────────────────────────────────────────────

class TestIterRecords:
    def test_yields_osint_records(self):
        kml = _make_kml([_make_placemark()])
        with patch("requests.get", return_value=_mock_response(kml)):
            records = list(iter_records())

        assert len(records) == 1
        assert isinstance(records[0], OSINTRecord)

    def test_osint_record_source_type_is_pdx911(self):
        kml = _make_kml([_make_placemark()])
        with patch("requests.get", return_value=_mock_response(kml)):
            records = list(iter_records())

        assert records[0].source_type == "PDX911"

    def test_osint_record_source_name(self):
        kml = _make_kml([_make_placemark()])
        with patch("requests.get", return_value=_mock_response(kml)):
            records = list(iter_records())

        assert records[0].source_name == "portlandmaps_911"

    def test_yields_empty_on_network_failure(self):
        with patch("requests.get", side_effect=ConnectionError("down")):
            records = list(iter_records())

        assert records == []

    def test_multiple_placemarks_yield_multiple_records(self):
        placemarks = [
            _make_placemark(
                title=f"INCIDENT{i} at {i}00 SE MAIN ST, PORT",
                desc=f"Thursday, June 20, 2024 0{i}:00 AM [Portland Police #PP2400000{i}]",
                lon=-122.6 + i * 0.01,
                lat=45.5 + i * 0.01,
            )
            for i in range(1, 4)
        ]
        kml = _make_kml(placemarks)
        with patch("requests.get", return_value=_mock_response(kml)):
            records = list(iter_records())

        assert len(records) == 3


# ── Pdx911Record ───────────────────────────────────────────────────────────────

class TestPdx911RecordMakeId:
    def test_deterministic_with_case_id(self):
        id1 = Pdx911Record.make_id("PP24001234", "THEFT", "100 NW BROADWAY")
        id2 = Pdx911Record.make_id("PP24001234", "THEFT", "100 NW BROADWAY")
        assert id1 == id2

    def test_different_inputs_produce_different_ids(self):
        id1 = Pdx911Record.make_id("PP24001234", "THEFT", "100 NW BROADWAY")
        id2 = Pdx911Record.make_id("PP24001235", "THEFT", "100 NW BROADWAY")
        assert id1 != id2

    def test_none_case_id_handled(self):
        record_id = Pdx911Record.make_id(None, "FIGHT", "200 SE DIVISION ST")
        assert isinstance(record_id, str)
        assert len(record_id) > 0

    def test_id_is_string(self):
        record_id = Pdx911Record.make_id("PP24001234", "ASSAULT", "300 NE BURNSIDE")
        assert isinstance(record_id, str)


class TestPdx911RecordToDict:
    def _make_record(self, **kwargs) -> Pdx911Record:
        defaults = dict(
            record_id="pdx911-abc123",
            case_id="PP24001234",
            agency="Portland Police",
            incident_type="THEFT",
            location_block="100 NW BROADWAY",
            timestamp=datetime(2024, 6, 20, 10, 30, tzinfo=timezone.utc),
            longitude=-122.6784,
            latitude=45.5231,
        )
        defaults.update(kwargs)
        return Pdx911Record(**defaults)

    def test_to_dict_contains_required_keys(self):
        d = self._make_record().to_dict()
        for key in ("record_id", "case_id", "agency", "incident_type", "location_block",
                    "timestamp", "geospatial", "collected_at", "metadata"):
            assert key in d

    def test_geospatial_with_coords(self):
        d = self._make_record(longitude=-122.6784, latitude=45.5231).to_dict()
        geo = d["geospatial"]
        assert geo["type"] == "Point"
        assert geo["coordinates"] == [-122.6784, 45.5231]

    def test_geospatial_without_coords_is_none(self):
        d = self._make_record(longitude=None, latitude=None).to_dict()
        assert d["geospatial"]["coordinates"] is None

    def test_timestamp_is_iso_string(self):
        d = self._make_record().to_dict()
        assert "T" in d["timestamp"]

    def test_none_timestamp_serialised_as_none(self):
        d = self._make_record(timestamp=None).to_dict()
        assert d["timestamp"] is None

    def test_none_case_id_preserved(self):
        d = self._make_record(case_id=None).to_dict()
        assert d["case_id"] is None


class TestPdx911RecordToOsintRecord:
    def _make_record(self, **kwargs) -> Pdx911Record:
        defaults = dict(
            record_id="pdx911-abc123",
            case_id="PP24001234",
            agency="Portland Police",
            incident_type="UNWANTED PERSON",
            location_block="1900 SE 6TH AVE",
            timestamp=datetime(2024, 6, 20, 10, 30, tzinfo=timezone.utc),
            longitude=-122.6584,
            latitude=45.5051,
        )
        defaults.update(kwargs)
        return Pdx911Record(**defaults)

    def test_returns_osint_record(self):
        r = self._make_record().to_osint_record()
        assert isinstance(r, OSINTRecord)

    def test_source_type_is_pdx911(self):
        r = self._make_record().to_osint_record()
        assert r.source_type == "PDX911"

    def test_source_name_is_portlandmaps_911(self):
        r = self._make_record().to_osint_record()
        assert r.source_name == "portlandmaps_911"

    def test_content_contains_incident_type(self):
        r = self._make_record(incident_type="ASSAULT").to_osint_record()
        assert "ASSAULT" in r.content

    def test_content_contains_location(self):
        r = self._make_record(location_block="500 SW MAIN ST").to_osint_record()
        assert "500 SW MAIN ST" in r.content

    def test_content_contains_coords_when_available(self):
        r = self._make_record(longitude=-122.6584, latitude=45.5051).to_osint_record()
        assert "45.50510" in r.content
        assert "-122.65840" in r.content

    def test_content_omits_coords_when_none(self):
        r = self._make_record(longitude=None, latitude=None).to_osint_record()
        assert "[" not in r.content

    def test_content_contains_agency(self):
        r = self._make_record(agency="Gresham Police").to_osint_record()
        assert "Gresham Police" in r.content

    def test_content_shows_na_when_no_case_id(self):
        r = self._make_record(case_id=None).to_osint_record()
        assert "N/A" in r.content

    def test_content_shows_case_id_when_present(self):
        r = self._make_record(case_id="PP24001234").to_osint_record()
        assert "PP24001234" in r.content

    def test_record_id_preserved(self):
        r = self._make_record(record_id="pdx911-abc123").to_osint_record()
        assert r.record_id == "pdx911-abc123"

    def test_url_is_portlandmaps(self):
        r = self._make_record().to_osint_record()
        assert "portlandmaps.com" in r.url
