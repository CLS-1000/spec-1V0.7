"""Tests for cls_pdx1 source adapters."""

from __future__ import annotations

import json


from cls_pdx1.models import Affiliation, Bill, BillStatus, ConfidenceTier, EdgeType
from cls_pdx1.sources.orestar import OrestarAdapter
from cls_pdx1.sources.olis import OlisAdapter
from cls_pdx1.sources.sei import SeiAdapter
from cls_pdx1.sources.wa_pdc import WaPdcAdapter


# ---------------------------------------------------------------------------
# ORESTAR
# ---------------------------------------------------------------------------

_ORESTAR_CSV = """\
filer_id,filer_name,transaction_type,amount,contributor_name,contributor_address,transaction_date,election_year
1001,Jane Smith,contribution,$5000.00,Acme Corp,123 Main St,01/15/2024,2024
1002,Bob Jones,contribution,$1200.50,XYZ LLC,456 Oak Ave,03/22/2024,2024
1003,,contribution,$500.00,Unknown,,,
"""


class TestOrestarAdapter:
    def test_parses_valid_rows(self):
        adapter = OrestarAdapter()
        result = adapter.fetch_from_csv_text(_ORESTAR_CSV)
        assert len(result.records) == 2  # row 3 skipped (no filer_name)

    def test_affiliation_type(self):
        adapter = OrestarAdapter()
        result = adapter.fetch_from_csv_text(_ORESTAR_CSV)
        assert all(isinstance(r, Affiliation) for r in result.records)

    def test_edge_type_is_donation(self):
        adapter = OrestarAdapter()
        result = adapter.fetch_from_csv_text(_ORESTAR_CSV)
        assert all(r.edge_type == EdgeType.DONATION for r in result.records)

    def test_confidence_is_hard_record(self):
        adapter = OrestarAdapter()
        result = adapter.fetch_from_csv_text(_ORESTAR_CSV)
        assert all(r.confidence == ConfidenceTier.HARD_RECORD for r in result.records)

    def test_amount_parsed(self):
        adapter = OrestarAdapter()
        result = adapter.fetch_from_csv_text(_ORESTAR_CSV)
        amounts = [r.amount for r in result.records]
        assert 5000.0 in amounts

    def test_missing_csv_returns_error(self):
        adapter = OrestarAdapter(csv_path="/nonexistent/path.csv")
        result = adapter.fetch()
        assert len(result.errors) > 0

    def test_no_path_returns_error(self):
        adapter = OrestarAdapter()
        result = adapter.fetch()
        assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# OLIS
# ---------------------------------------------------------------------------

_OLIS_BILLS = [
    {
        "MeasureNumber": "HB 1234",
        "RelatingClause": "An act relating to housing",
        "CurrentStatus": "In Committee",
        "Chamber": "House",
        "ChiefSponsor": "Rep. Smith",
        "source_url": "https://oregonlegislature.gov/bills/HB1234",
    },
    {
        "MeasureNumber": "SB 567",
        "RelatingClause": "An act relating to utilities",
        "CurrentStatus": "Passed Both Chambers",
        "Chamber": "Senate",
        "ChiefSponsor": "Sen. Jones",
        "source_url": "https://oregonlegislature.gov/bills/SB567",
    },
    {
        "MeasureNumber": "",   # should be skipped
        "RelatingClause": "Bad bill",
        "CurrentStatus": "Introduced",
        "Chamber": "House",
        "source_url": "https://oregonlegislature.gov/",
    },
]


class TestOlisAdapter:
    def test_parses_valid_bills(self):
        adapter = OlisAdapter(bill_data=_OLIS_BILLS)
        result = adapter.fetch()
        assert len(result.records) == 2

    def test_bill_type(self):
        adapter = OlisAdapter(bill_data=_OLIS_BILLS)
        result = adapter.fetch()
        assert all(isinstance(r, Bill) for r in result.records)

    def test_status_in_committee(self):
        adapter = OlisAdapter(bill_data=_OLIS_BILLS[:1])
        result = adapter.fetch()
        assert result.records[0].status == BillStatus.IN_COMMITTEE

    def test_status_passed_both_chambers(self):
        adapter = OlisAdapter(bill_data=_OLIS_BILLS[1:2])
        result = adapter.fetch()
        assert result.records[0].status == BillStatus.PASSED_BOTH_CHAMBERS

    def test_no_data_returns_error(self):
        adapter = OlisAdapter()
        result = adapter.fetch()
        assert len(result.errors) > 0

    def test_sponsor_captured(self):
        adapter = OlisAdapter(bill_data=_OLIS_BILLS[:1])
        result = adapter.fetch()
        assert result.records[0].sponsor == "Rep. Smith"


# ---------------------------------------------------------------------------
# SEI
# ---------------------------------------------------------------------------

_SEI_RECORDS = [
    {
        "official_name": "Commissioner A",
        "role": "City Commissioner",
        "year": 2024,
        "source_url": "https://www.oregon.gov/ogec/pages/sei.aspx",
        "business_interests": [
            {"entity_name": "Realty Corp", "amount": 50000},
            {"entity_name": "Tech LLC", "amount": 0},
        ],
        "gifts": [
            {"donor": "Business PAC", "amount": 150},
        ],
    },
    {
        "official_name": "Senator B",
        "role": "State Senator",
        "year": 2024,
        "source_url": "https://www.oregon.gov/ogec/pages/sei.aspx",
        "business_interests": [],
        "gifts": [],
    },
]


class TestSeiAdapter:
    def test_parses_business_interests(self):
        adapter = SeiAdapter(records=_SEI_RECORDS)
        result = adapter.fetch()
        employment_affs = [r for r in result.records if r.edge_type == EdgeType.EMPLOYMENT]
        assert len(employment_affs) == 2  # 2 business interests for Commissioner A

    def test_parses_gifts(self):
        adapter = SeiAdapter(records=_SEI_RECORDS)
        result = adapter.fetch()
        gift_affs = [r for r in result.records if r.edge_type == EdgeType.DONATION]
        assert len(gift_affs) == 1

    def test_all_hard_record(self):
        adapter = SeiAdapter(records=_SEI_RECORDS)
        result = adapter.fetch()
        assert all(r.confidence == ConfidenceTier.HARD_RECORD for r in result.records)

    def test_missing_official_name_skipped(self):
        bad = [{"official_name": "", "role": "Mayor", "business_interests": [{"entity_name": "Corp"}], "gifts": []}]
        adapter = SeiAdapter(records=bad)
        result = adapter.fetch()
        assert len(result.records) == 0

    def test_jsonl_file(self, tmp_path):
        jsonl = tmp_path / "sei.jsonl"
        jsonl.write_text(
            "\n".join(json.dumps(r) for r in _SEI_RECORDS),
            encoding="utf-8",
        )
        adapter = SeiAdapter(jsonl_path=jsonl)
        result = adapter.fetch()
        assert len(result.records) >= 1

    def test_missing_jsonl_returns_error(self):
        adapter = SeiAdapter(jsonl_path="/nonexistent/sei.jsonl")
        result = adapter.fetch()
        assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# WA PDC
# ---------------------------------------------------------------------------

_WA_PDC_RECORDS = [
    {
        "filer_name": "Candidate X",
        "contributor_name": "Real Estate PAC",
        "amount": "10000",
        "receipt_date": "2024-04-15",
    },
    {
        "filer_name": "",   # should be skipped
        "contributor_name": "Nobody",
        "amount": "100",
        "receipt_date": "2024-01-01",
    },
]


class TestWaPdcAdapter:
    def test_parses_valid_records(self):
        adapter = WaPdcAdapter(records=_WA_PDC_RECORDS)
        result = adapter.fetch()
        assert len(result.records) == 1

    def test_edge_type_donation(self):
        adapter = WaPdcAdapter(records=_WA_PDC_RECORDS)
        result = adapter.fetch()
        assert result.records[0].edge_type == EdgeType.DONATION

    def test_amount_parsed(self):
        adapter = WaPdcAdapter(records=_WA_PDC_RECORDS)
        result = adapter.fetch()
        assert result.records[0].amount == 10000.0

    def test_no_records_returns_error(self):
        adapter = WaPdcAdapter()
        result = adapter.fetch()
        assert len(result.errors) > 0
