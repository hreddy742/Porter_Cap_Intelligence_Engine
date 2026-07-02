"""Tests for Connecticut UCC ingestion."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porter_verify.connectors.connecticut_ucc import ingest_ct_ucc_rows
from porter_verify.db.models import UccFiling


def test_ingest_connecticut_ucc_row_maps_and_classifies(db_session: Session) -> None:
    rows = [
        {
            "id_lien_flng_nbr": "0005229652",
            "id_ucc_flng_nbr": "0005229652",
            "lien_status": "Active",
            "cd_flng_type": "ORIG FIN STMT",
            "tx_lien_descript": "OFS",
            "debtor_nm_bus": "CONSTITUTION SURGERY CENTER EAST, LLC",
            "debtor_ad_str1": "140 CROSS RD",
            "debtor_ad_city": "WATERFORD",
            "debtor_ad_state": "CT",
            "debtor_ad_zip": "06385",
            "sec_party_nm_bus": "DE LAGE LANDEN FINANCIAL SERVICES, INC.",
            "dt_accept": "2024-07-19T00:00:00.000",
        }
    ]

    assert ingest_ct_ucc_rows(db_session, rows) == 1

    filing = db_session.get(UccFiling, "CT:0005229652")
    assert filing is not None
    assert filing.filing_type == "UCC1"
    assert filing.status == "ACTIVE"
    assert filing.debtor_normalized == "CONSTITUTION SURGERY CENTER EAST LLC"
    assert filing.lender_type == "BANK"


def test_ingest_connecticut_termination_sets_ucc3_and_termination_date(
    db_session: Session,
) -> None:
    rows = [
        {
            "id_lien_flng_nbr": "0003279557",
            "id_ucc_flng_nbr": "0003279651",
            "lien_status": "Terminated",
            "cd_flng_type": "TERMINATION",
            "debtor_nm_bus": "T-AHIRT ETC.",
            "sec_party_nm_bus": "CONNECTICUT DEPARTMENT OF LABOR",
            "dt_accept": "2018-12-12T00:00:00.000",
        }
    ]

    assert ingest_ct_ucc_rows(db_session, rows) == 1

    filing = db_session.get(UccFiling, "CT:0003279651")
    assert filing is not None
    assert filing.filing_type == "UCC3"
    assert filing.status == "TERMINATED"
    assert filing.termination_date is not None
