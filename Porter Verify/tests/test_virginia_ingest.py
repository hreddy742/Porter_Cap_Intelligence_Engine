"""Tests for Virginia business entity parsing and ingestion."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.connectors.virginia import parse_va_record
from porter_verify.connectors.virginia_ingest import ingest_va_file
from porter_verify.db.models import VaBusinessEntity


def test_parse_virginia_record_maps_common_columns() -> None:
    record = parse_va_record(
        {
            "Entity ID": "11412345",
            "Entity Name": "Old Dominion Freight LLC",
            "Status": "Active",
            "Entity Type": "Limited Liability Company",
            "Formation Date": "06/01/2026",
        }
    )

    assert record.entity_id == "11412345"
    assert record.legal_name == "Old Dominion Freight LLC"
    assert record.source_record_url == (
        "https://cis.scc.virginia.gov/EntitySearch/BusinessInformation?businessId=11412345"
    )


def test_ingest_virginia_file_upserts_rows(db_session: Session, tmp_path: Path) -> None:
    csv_path = tmp_path / "virginia.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Entity ID,Entity Name,Status,Entity Type,Formation Date",
                "11412345,Old Dominion Freight LLC,Active,Limited Liability Company,06/01/2026",
                "11412346,Richmond Hauling Inc,Active,Corporation,2026-06-02",
            ]
        ),
        encoding="utf-8",
    )

    assert ingest_va_file(db_session, csv_path) == 2

    rows = db_session.scalars(
        select(VaBusinessEntity).order_by(VaBusinessEntity.entity_id)
    ).all()
    assert [row.entity_name for row in rows] == ["Old Dominion Freight LLC", "Richmond Hauling Inc"]
    assert rows[0].normalized_name == "old dominion freight llc"
