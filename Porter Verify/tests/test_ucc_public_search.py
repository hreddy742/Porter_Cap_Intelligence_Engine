"""Tests for public-search UCC result ingestion."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from porter_verify.db.models import UccFiling
from porter_verify.services.ucc_public_search import (
    PublicSearchUccResult,
    ingest_public_search_results,
    ucc_name_variants,
)


def test_ucc_name_variants_remove_common_suffixes() -> None:
    assert ucc_name_variants("Acme Logistics LLC") == [
        "Acme Logistics LLC",
        "ACME LOGISTICS LLC",
        "ACME LOGISTICS",
    ]


def test_ingest_public_search_result_marks_provenance_and_classifies(
    db_session: Session,
) -> None:
    count = ingest_public_search_results(
        db_session,
        [
            PublicSearchUccResult(
                state="NJ",
                filing_id="2026001",
                debtor_name="Acme Logistics LLC",
                filing_type="UCC1",
                status="Active",
                secured_party_name="First National Bank",
                filing_date=date(2026, 6, 1),
                search_query="Acme Logistics",
                source_url="https://www.njportal.com/UCC/Search/NonCertifiedSearch.aspx",
                match_confidence=95,
            )
        ],
    )

    assert count == 1
    filing = db_session.get(UccFiling, "NJ:SEARCH:2026001")
    assert filing is not None
    assert filing.acquisition_method == "PUBLIC_SEARCH"
    assert filing.search_query == "Acme Logistics"
    assert filing.match_confidence == 95
    assert filing.lender_type == "BANK"
