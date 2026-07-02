"""Tests for Florida Sunbiz business entity parsing and ingestion."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.connectors.florida import parse_fl_date, parse_fl_fixed_width, parse_fl_record
from porter_verify.connectors.florida_ingest import ingest_fl_file
from porter_verify.db.models import FlBusinessEntity


def _fixed_width(**fields: tuple[int, int, str]) -> str:
    chars = [" "] * 1440
    for start, end, value in fields.values():
        chars[start - 1 : end] = list(value.ljust(end - start + 1)[: end - start + 1])
    return "".join(chars)


def test_parse_florida_fixed_width_record() -> None:
    line = _fixed_width(
        entity=(1, 12, "L26000000001"),
        name=(13, 204, "Sunshine Freight LLC"),
        status=(205, 205, "A"),
        filing_type=(206, 209, "FLAL"),
        file_date=(473, 480, "20260601"),
        agent=(545, 586, "Jane Agent"),
    )

    record = parse_fl_fixed_width(line)

    assert record.entity_id == "L26000000001"
    assert record.legal_name == "Sunshine Freight LLC"
    assert record.formation_date is not None
    assert record.source_record_url is not None


def test_parse_florida_csv_record_maps_common_columns() -> None:
    record = parse_fl_record(
        {
            "Document Number": "P26000000002",
            "Corporate Name": "Tampa Hauling Inc",
            "Status": "ACTIVE",
            "Filing Type": "Domestic Profit Corporation",
            "File Date": "06/02/2026",
        }
    )

    assert record.entity_id == "P26000000002"
    assert record.legal_name == "Tampa Hauling Inc"
    assert record.jurisdiction == "FL"


def test_parse_florida_date_rejects_impossible_future_year() -> None:
    assert parse_fl_date("62220206") is None


def test_parse_florida_date_rejects_future_date() -> None:
    tomorrow = date.today() + timedelta(days=1)
    assert parse_fl_date(tomorrow.strftime("%m%d%Y")) is None


def test_ingest_florida_file_upserts_fixed_width_rows(
    db_session: Session, tmp_path: Path
) -> None:
    path = tmp_path / "florida.txt"
    path.write_text(
        _fixed_width(
            entity=(1, 12, "L26000000001"),
            name=(13, 204, "Sunshine Freight LLC"),
            status=(205, 205, "A"),
            filing_type=(206, 209, "FLAL"),
            file_date=(473, 480, "20260601"),
        ),
        encoding="utf-8",
    )

    assert ingest_fl_file(db_session, path) == 1

    row = db_session.scalar(select(FlBusinessEntity))
    assert row is not None
    assert row.entity_name == "Sunshine Freight LLC"
    assert row.normalized_name == "sunshine freight llc"
