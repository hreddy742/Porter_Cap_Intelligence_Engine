"""Tests for Oregon UCC ingestion."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porter_verify.connectors.oregon_ucc import ingest_or_ucc_rows
from porter_verify.db.models import UccFiling


def test_ingest_oregon_monthly_ucc_group_maps_debtor_and_secured_party(
    db_session: Session,
) -> None:
    rows = [
        {
            "_source_dataset": "monthly",
            "file_number": "12345",
            "file_type": "INITIAL",
            "filing_date": "2026-05-15T00:00:00.000",
            "party_type": "DB",
            "entity": "JRA CYCLING, INC.",
            "mail_addr_1": "2480 ALDER STREET",
            "city_descr": "EUGENE",
            "st_cd_txt": "OR",
            "zip_code_txt": "97405",
        },
        {
            "_source_dataset": "monthly",
            "file_number": "12345",
            "file_type": "INITIAL",
            "party_type": "SP",
            "entity": "CITIZENS BANK",
        },
    ]

    assert ingest_or_ucc_rows(db_session, rows) == 1

    filing = db_session.get(UccFiling, "OR:MONTHLY:12345")
    assert filing is not None
    assert filing.filing_type == "UCC1"
    assert filing.status == "ACTIVE"
    assert filing.debtor_normalized == "JRA CYCLING INC"
    assert filing.secured_party_name == "CITIZENS BANK"
    assert filing.lender_type == "BANK"


def test_ingest_oregon_farm_product_lien_uses_lookup_secured_party(
    db_session: Session,
) -> None:
    rows = [
        {
            "_source_dataset": "farm_products",
            "file_number": "314157",
            "lien_type": "EFS",
            "entity_name": "HARRIS, CYNTHIA L",
            "secured_party_lookup": '["FARM SERVICE AGENCY"]',
            "filing_date": "1988-02-08T00:00:00.000",
            "entity_type": "DB",
            "address_1": "7816 LAKESIDE DR NE",
            "city": "SALEM",
            "state": "OR",
            "zip_code": "97305",
            "product": "0310 Ryegrass",
            "county": "24 Marion",
            "crop_yr": "ALL",
        }
    ]

    assert ingest_or_ucc_rows(db_session, rows) == 1

    filing = db_session.get(UccFiling, "OR:FARM_PRODUCTS:314157")
    assert filing is not None
    assert filing.filing_type == "UCC1"
    assert filing.status == "ACTIVE"
    assert filing.secured_party_name == "FARM SERVICE AGENCY"
    assert (
        filing.collateral_description
        == "Products: 0310 Ryegrass; County: 24 Marion; Crop year: ALL"
    )
