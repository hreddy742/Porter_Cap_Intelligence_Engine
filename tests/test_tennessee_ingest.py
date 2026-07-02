"""Tests for Tennessee business entity parsing and ingestion."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.connectors.tennessee import parse_tn_record
from porter_verify.connectors.tennessee_ingest import ingest_tn_file
from porter_verify.db.models import TnBusinessEntity


def test_parse_tennessee_record_maps_common_columns() -> None:
    record = parse_tn_record(
        {
            "Control Number": "001234567",
            "Business Name": "Volunteer Freight LLC",
            "Business Status": "Active",
            "Business Type": "Limited Liability Company",
            "Formation Date": "06/01/2026",
        }
    )

    assert record.entity_id == "001234567"
    assert record.legal_name == "Volunteer Freight LLC"
    assert record.source_record_url == "https://tnbear.tn.gov/Ecommerce/FilingSearch.aspx?CN=001234567"


def test_ingest_tennessee_file_upserts_rows(db_session: Session, tmp_path: Path) -> None:
    csv_path = tmp_path / "tennessee.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Control Number,Business Name,Business Status,Business Type,Formation Date",
                "001234567,Volunteer Freight LLC,Active,Limited Liability Company,06/01/2026",
                "001234568,Nashville Hauling Inc,Active,Corporation,2026-06-02",
            ]
        ),
        encoding="utf-8",
    )

    assert ingest_tn_file(db_session, csv_path) == 2

    rows = db_session.scalars(
        select(TnBusinessEntity).order_by(TnBusinessEntity.entity_id)
    ).all()
    assert [row.entity_name for row in rows] == ["Volunteer Freight LLC", "Nashville Hauling Inc"]
    assert rows[0].normalized_name == "volunteer freight llc"
