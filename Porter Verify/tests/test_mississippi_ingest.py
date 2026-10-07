"""Tests for Mississippi business entity parsing and ingestion."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.connectors.mississippi import parse_ms_record
from porter_verify.connectors.mississippi_ingest import ingest_ms_file
from porter_verify.db.models import MsBusinessEntity


def test_parse_mississippi_record_maps_common_columns() -> None:
    record = parse_ms_record(
        {
            "Business ID": "1234567",
            "Business Name": "Magnolia Freight LLC",
            "Business Status": "Good Standing",
            "Business Type": "Limited Liability Company",
            "Formation Date": "06/01/2026",
        }
    )

    assert record.entity_id == "1234567"
    assert record.legal_name == "Magnolia Freight LLC"
    assert record.source_record_url == (
        "https://corp.sos.ms.gov/corp/portal/c/page/corpBusinessIdSearch/portal.aspx?businessId=1234567"
    )


def test_ingest_mississippi_file_upserts_rows(db_session: Session, tmp_path: Path) -> None:
    csv_path = tmp_path / "mississippi.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Business ID,Business Name,Business Status,Business Type,Formation Date",
                "1234567,Magnolia Freight LLC,Good Standing,Limited Liability Company,06/01/2026",
                "1234568,Jackson Hauling Inc,Good Standing,Corporation,2026-06-02",
            ]
        ),
        encoding="utf-8",
    )

    assert ingest_ms_file(db_session, csv_path) == 2

    rows = db_session.scalars(
        select(MsBusinessEntity).order_by(MsBusinessEntity.entity_id)
    ).all()
    assert [row.entity_name for row in rows] == ["Magnolia Freight LLC", "Jackson Hauling Inc"]
    assert rows[0].normalized_name == "magnolia freight llc"
