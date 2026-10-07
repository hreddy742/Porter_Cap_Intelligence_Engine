"""Tests for Alabama business entity parsing and ingestion."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.connectors.alabama import parse_al_record
from porter_verify.connectors.alabama_ingest import ingest_al_file
from porter_verify.db.models import AlBusinessEntity


def test_parse_alabama_record_maps_common_columns() -> None:
    record = parse_al_record(
        {
            "Entity ID": "000123456",
            "Entity Name": "Bama Freight LLC",
            "Status": "Exists",
            "Entity Type": "Domestic Limited Liability Company",
            "Formation Date": "06/01/2026",
            "Principal Address": "100 Commerce St Montgomery AL 36104",
            "Registered Agent": "Jane Agent",
        }
    )

    assert record.entity_id == "000123456"
    assert record.legal_name == "Bama Freight LLC"
    assert record.formation_date is not None
    assert record.source_record_url == (
        "https://arc-sos.state.al.us/cgi/corpdetail.mbr/detail?corp=000123456"
    )


def test_ingest_alabama_file_upserts_rows(db_session: Session, tmp_path: Path) -> None:
    csv_path = tmp_path / "alabama.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Entity ID,Entity Name,Status,Entity Type,Formation Date,Principal Address",
                "000123456,Bama Freight LLC,Exists,Domestic Limited Liability Company,"
                "06/01/2026,100 Commerce St",
                "000987654,Mobile Hauling Inc,Exists,Domestic Corporation,2026-06-02,200 Port Rd",
            ]
        ),
        encoding="utf-8",
    )

    assert ingest_al_file(db_session, csv_path) == 2

    rows = db_session.scalars(
        select(AlBusinessEntity).order_by(AlBusinessEntity.entity_id)
    ).all()
    assert [row.entity_name for row in rows] == ["Bama Freight LLC", "Mobile Hauling Inc"]
    assert rows[0].normalized_name == "bama freight llc"
