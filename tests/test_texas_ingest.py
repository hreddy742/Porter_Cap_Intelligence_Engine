"""Tests for Texas business entity parsing and ingestion."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.connectors.texas import parse_tx_record
from porter_verify.connectors.texas_ingest import ingest_tx_file
from porter_verify.db.models import TxBusinessEntity


def test_parse_texas_record_maps_common_columns() -> None:
    record = parse_tx_record(
        {
            "File Number": "0801234567",
            "Entity Name": "Lone Star Freight LLC",
            "Status": "In Existence",
            "Entity Type": "Domestic Limited Liability Company",
            "Formation Date": "06/01/2026",
        }
    )

    assert record.entity_id == "0801234567"
    assert record.legal_name == "Lone Star Freight LLC"
    assert record.source_record_url == "https://mycpa.cpa.state.tx.us/coa/search.do"


def test_ingest_texas_file_upserts_rows(db_session: Session, tmp_path: Path) -> None:
    csv_path = tmp_path / "texas.csv"
    csv_path.write_text(
        "\n".join(
            [
                "File Number,Entity Name,Status,Entity Type,Formation Date",
                "0801234567,Lone Star Freight LLC,In Existence,Domestic LLC,06/01/2026",
                "0801234568,Dallas Hauling Inc,In Existence,Domestic Corporation,2026-06-02",
            ]
        ),
        encoding="utf-8",
    )

    assert ingest_tx_file(db_session, csv_path) == 2

    rows = db_session.scalars(
        select(TxBusinessEntity).order_by(TxBusinessEntity.entity_id)
    ).all()
    assert [row.entity_name for row in rows] == ["Lone Star Freight LLC", "Dallas Hauling Inc"]
    assert rows[0].normalized_name == "lone star freight llc"
