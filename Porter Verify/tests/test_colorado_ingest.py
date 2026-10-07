"""Tests for the Colorado CSV ingest (Feature 2)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.connectors.colorado_ingest import ingest_co_csv
from porter_verify.db.models import CoBusinessEntity

CSV_HEADER = (
    "entityid,entityname,entitystatus,entitytype,entityformdate,"
    "principaladdress1,principalcity,principalstate,principalzipcode,"
    "agentfirstname,agentlastname,agentorganizationname\n"
)
CSV_ROWS = (
    "20251665680,KYLDERON MIST VALLEY LLC,Good Standing,DLLC,2025-06-16T00:00:00.000,"
    "123 Main St,Delta,CO,81416,,,Registered Agents Inc\n"
    '19871342214,"SOUTHWEST CONTRACTING, LLC",Delinquent,DLLC,1978-02-28T00:00:00.000,'
    ",Cortez,CO,,Maria,Franchini,\n"
    ",NO ID SHOULD BE SKIPPED,Good Standing,DLLC,,,,,,,,\n"  # skipped: no entity id
)


def _write_csv(tmp_path: Path) -> Path:
    path = tmp_path / "co.csv"
    path.write_text(CSV_HEADER + CSV_ROWS, encoding="utf-8")
    return path


def test_ingest_loads_valid_rows_and_skips_idless(tmp_path: Path, db_session: Session) -> None:
    count = ingest_co_csv(db_session, _write_csv(tmp_path))
    assert count == 2  # the id-less row is skipped

    rows = list(db_session.scalars(select(CoBusinessEntity)))
    assert len(rows) == 2
    by_id = {r.entity_id: r for r in rows}
    assert by_id["20251665680"].normalized_name == "kylderon mist valley llc"
    assert by_id["20251665680"].agent_name == "Registered Agents Inc"
    assert by_id["19871342214"].status_raw == "Delinquent"


def test_ingest_is_idempotent(tmp_path: Path, db_session: Session) -> None:
    path = _write_csv(tmp_path)
    ingest_co_csv(db_session, path)
    ingest_co_csv(db_session, path)  # re-ingest

    rows = list(db_session.scalars(select(CoBusinessEntity)))
    assert len(rows) == 2  # upsert by entity_id — no duplicates


def test_ingest_preserves_raw_row(tmp_path: Path, db_session: Session) -> None:
    ingest_co_csv(db_session, _write_csv(tmp_path))
    row = db_session.get(CoBusinessEntity, "20251665680")
    assert row is not None
    assert row.raw["entityname"] == "KYLDERON MIST VALLEY LLC"
