"""Tests for Florida UCC ingestion."""

from __future__ import annotations

import zipfile

from sqlalchemy.orm import Session

from porter_verify.connectors.florida_ucc import ingest_fl_ucc_zip_dir
from porter_verify.db.models import UccFiling


def test_ingest_florida_ucc_zip_dir_maps_active_and_termination(
    db_session: Session,
    tmp_path,
) -> None:  # noqa: ANN001
    _write_zip(
        tmp_path / "filings_full.zip",
        "filings.csv",
        "Ucc1FilingNumber|FilingDate|FilingStatus\n"
        "2001|06/05/2025|Filed\n"
        "2002|06/05/2002|Lapsed\n",
    )
    _write_zip(
        tmp_path / "debtors_full.zip",
        "debtors.csv",
        "Ucc1FilingNumber|DebName|DebAddressLine1|DebCity|DebState|DebZipCode\n"
        "2001|ACME LOGISTICS LLC|1 MAIN ST|MIAMI|FL|33101\n",
    )
    _write_zip(
        tmp_path / "secureds_full.zip",
        "secureds.csv",
        "Ucc1FilingNumber|SecName\n"
        "2001|Riviera Finance\n",
    )
    _write_zip(
        tmp_path / "events_full.zip",
        "events.csv",
        "Ucc3FilingNumber|Ucc1FilingNumber|EventDate|ActionVerbage\n"
        "3001|0000002001|07/01/2026|TERMINATION\n",
    )

    assert ingest_fl_ucc_zip_dir(db_session, tmp_path) == 2

    active = db_session.get(UccFiling, "FL:UCC1:2001")
    termination = db_session.get(UccFiling, "FL:UCC3:3001")
    lapsed = db_session.get(UccFiling, "FL:UCC1:2002")
    assert active is not None
    assert active.status == "ACTIVE"
    assert active.debtor_normalized == "ACME LOGISTICS LLC"
    assert active.is_factoring_related is True
    assert termination is not None
    assert termination.status == "TERMINATED"
    assert termination.termination_date is not None
    assert lapsed is None


def _write_zip(path, name: str, content: str) -> None:  # noqa: ANN001
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, content)
