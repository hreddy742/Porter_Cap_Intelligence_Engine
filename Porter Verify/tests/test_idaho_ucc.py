"""Tests for Idaho targeted UCC public-search mapping."""

from __future__ import annotations

from datetime import date

from porter_verify.connectors.idaho_ucc import (
    _result_from_row as idaho_result_from_row,
)
from porter_verify.connectors.idaho_ucc import (
    to_public_search_results,
)


def test_idaho_ucc_result_maps_public_api_row() -> None:
    row = idaho_result_from_row(
        {
            "TITLE": [" CONSTRUCTION, INC. - NORTH SALT LAKE, UT"],
            "RECORD_TYPE": "Initial",
            "RECORD_NUM": "20102496473",
            "SEC_PARTY": "NORTHWEST FARM CREDIT SERVICES, FLCA - BURLEY, ID",
            "FILING_DATE": "12/08/2010",
            "STATUS": "Active",
        }
    )

    assert row.debtor_name == "CONSTRUCTION, INC."
    assert row.filing_number == "20102496473"
    assert row.secured_party == "NORTHWEST FARM CREDIT SERVICES, FLCA - BURLEY, ID"
    assert row.filing_date == date(2010, 12, 8)


def test_idaho_ucc_public_search_result_has_provenance() -> None:
    row = idaho_result_from_row(
        {
            "TITLE": [" CONSTRUCTION, INC. - NORTH SALT LAKE, UT"],
            "RECORD_TYPE": "Initial",
            "RECORD_NUM": "20102496473",
            "SEC_PARTY": "NORTHWEST FARM CREDIT SERVICES, FLCA - BURLEY, ID",
            "FILING_DATE": "12/08/2010",
            "STATUS": "Active",
        }
    )

    result = to_public_search_results("CONSTRUCTION", [row])[0]

    assert result.state == "ID"
    assert result.filing_id == "20102496473"
    assert result.debtor_name == "CONSTRUCTION, INC."
    assert result.secured_party_name == "NORTHWEST FARM CREDIT SERVICES, FLCA - BURLEY, ID"
    assert result.match_confidence == 90
