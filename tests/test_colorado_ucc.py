"""Tests for Colorado UCC ingestion."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porter_verify.connectors.colorado_ucc import ingest_co_ucc_csv_dir, ingest_co_ucc_rows
from porter_verify.db.models import UccFiling


def test_ingest_colorado_ucc_row_maps_related_records(db_session: Session) -> None:
    rows = [
        {
            "transactionid": "2004F062713",
            "fileid": "244288",
            "transactiontype": "Initial Filing",
            "filingdate": "2004-06-07T00:00:00.000",
            "filingtype": "ucc",
            "documenttype": "UCC financing statement",
            "terminationflag": False,
            "debtor": {
                "organizationname": "BURT CHEVROLET INC",
                "address1": "5200 S BROADWAY",
                "city": "ENGLEWOOD",
                "state": "CO",
                "zipcode": "80110",
            },
            "secured_party": {
                "organizationname": "FIRST NATIONAL BANK",
                "address1": "100 MAIN",
            },
            "collateral": {"collateraldescription": "ALL ASSETS"},
        }
    ]

    assert ingest_co_ucc_rows(db_session, iter(rows)) == 1

    filing = db_session.get(UccFiling, "CO:2004F062713")
    assert filing is not None
    assert filing.filing_type == "UCC1"
    assert filing.status == "ACTIVE"
    assert filing.debtor_normalized == "BURT CHEVROLET INC"
    assert filing.lender_type == "BANK"
    assert filing.collateral_description == "ALL ASSETS"


def test_ingest_colorado_termination_maps_to_ucc3(db_session: Session) -> None:
    rows = [
        {
            "transactionid": "20152046565",
            "fileid": "1215993",
            "transactiontype": "Amendment",
            "filingdate": "2015-05-20T00:00:00.000",
            "documenttype": "Termination",
            "terminationflag": True,
            "debtor": {"organizationname": "ACME LLC"},
            "secured_party": {"organizationname": "Riviera Finance"},
            "collateral": {},
        }
    ]

    assert ingest_co_ucc_rows(db_session, iter(rows)) == 1

    filing = db_session.get(UccFiling, "CO:20152046565")
    assert filing is not None
    assert filing.filing_type == "UCC3"
    assert filing.status == "TERMINATED"
    assert filing.is_factoring_related is True
    assert filing.termination_date is not None


def test_ingest_colorado_csv_dir_maps_camel_case_headers(
    db_session: Session, tmp_path
) -> None:  # noqa: ANN001
    (tmp_path / "filing.csv").write_text(
        "transactionId,transactionType,filingDate,filingType,documentType,terminationFlag,fileId\n"
        "CO1,Initial Filing,06/07/2004,ucc,UCC financing statement,false,1\n",
        encoding="utf-8",
    )
    (tmp_path / "debtor.csv").write_text(
        "debtorid,fileid,organizationname,address1,city,state,zipcode\n"
        "1,1,BURT CHEVROLET INC,5200 S BROADWAY,ENGLEWOOD,CO,80110\n",
        encoding="utf-8",
    )
    (tmp_path / "secured_party.csv").write_text(
        "spId,fileId,organizationName,address1\n"
        "1,1,FIRST NATIONAL BANK,100 MAIN\n",
        encoding="utf-8",
    )
    (tmp_path / "collateral.csv").write_text(
        "collateralid,fileid,collateraldescription\n"
        "1,1,ALL ASSETS\n",
        encoding="utf-8",
    )

    assert ingest_co_ucc_csv_dir(db_session, tmp_path) == 1
    filing = db_session.get(UccFiling, "CO:CO1")
    assert filing is not None
    assert filing.debtor_name == "BURT CHEVROLET INC"
    assert filing.secured_party_name == "FIRST NATIONAL BANK"
    assert filing.lender_type == "BANK"
