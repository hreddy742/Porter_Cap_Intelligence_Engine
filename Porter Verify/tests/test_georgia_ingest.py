"""Tests for Georgia business entity parsing and ingestion."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.connectors.georgia import parse_ga_record
from porter_verify.connectors.georgia_ingest import ingest_ga_file
from porter_verify.db.models import GaBusinessEntity


def test_parse_georgia_record_maps_common_columns() -> None:
    record = parse_ga_record(
        {
            "Control Number": "26012345",
            "Business Name": "Peach Freight LLC",
            "Business Status": "Active/Compliance",
            "Business Type": "Domestic Limited Liability Company",
            "Date Formed": "06/01/2026",
            "Principal Office Address": "100 Peachtree St Atlanta GA 30303",
            "Registered Agent Name": "Jane Agent",
        }
    )

    assert record.entity_id == "26012345"
    assert record.legal_name == "Peach Freight LLC"
    assert record.status_raw == "Active/Compliance"
    assert record.source_record_url == (
        "https://ecorp.sos.ga.gov/BusinessSearch/BusinessInformation?businessId=26012345"
    )


def test_ingest_georgia_file_upserts_rows(db_session: Session, tmp_path: Path) -> None:
    csv_path = tmp_path / "georgia.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Control Number,Business Name,Business Status,Business Type,Date Formed",
                "26012345,Peach Freight LLC,Active/Compliance,"
                "Domestic Limited Liability Company,06/01/2026",
                "26067890,Savannah Hauling Inc,Active/Compliance,"
                "Domestic Profit Corporation,2026-06-02",
            ]
        ),
        encoding="utf-8",
    )

    assert ingest_ga_file(db_session, csv_path) == 2

    rows = db_session.scalars(
        select(GaBusinessEntity).order_by(GaBusinessEntity.entity_id)
    ).all()
    assert [row.entity_name for row in rows] == ["Peach Freight LLC", "Savannah Hauling Inc"]
    assert rows[0].normalized_name == "peach freight llc"
