"""Tests for the Colorado open-data connector (Feature 3).

Includes the SourceConnector contract checks (proving it is swappable like any other
connector) plus Colorado-specific behavior.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from porter_verify.connectors.base import (
    ConnectorQuery,
    RawRecord,
    RawResult,
    SourceConnector,
    SourceHealth,
    SourceRef,
)
from porter_verify.connectors.colorado_connector import ColoradoOpenDataConnector
from porter_verify.connectors.colorado_ingest import ingest_co_csv
from porter_verify.db import models  # noqa: F401
from porter_verify.db.base import Base

_CSV = (
    "entityid,entityname,entitystatus,entitytype,entityformdate,principalcity,"
    "principalstate,agentlastname,agentorganizationname\n"
    "20251665680,KYLDERON MIST VALLEY LLC,Good Standing,DLLC,2025-06-16T00:00:00.000,"
    "Delta,CO,,Registered Agents Inc\n"
    '19871342214,"SOUTHWEST CONTRACTING, LLC",Delinquent,DLLC,1978-02-28T00:00:00.000,'
    "Cortez,CO,Franchini,\n"
)


@pytest.fixture
def connector(tmp_path) -> Iterator[ColoradoOpenDataConnector]:
    engine: Engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record):  # noqa: ANN001
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    csv_path = tmp_path / "co.csv"
    csv_path.write_text(_CSV, encoding="utf-8")
    with factory() as s:
        ingest_co_csv(s, csv_path)

    yield ColoradoOpenDataConnector(factory)
    engine.dispose()


# --- contract -------------------------------------------------------------


def test_satisfies_connector_protocol(connector: ColoradoOpenDataConnector) -> None:
    assert isinstance(connector, SourceConnector)
    assert connector.name and isinstance(connector.capabilities, set)
    assert connector.states == {"CO"}


def test_search_returns_raw_results(connector: ColoradoOpenDataConnector) -> None:
    results = connector.search(ConnectorQuery(name="KYLDERON", state="CO"))
    assert all(isinstance(r, RawResult) for r in results)
    assert any(r.legal_name == "KYLDERON MIST VALLEY LLC" for r in results)


def test_health_reports_ingested_count(connector: ColoradoOpenDataConnector) -> None:
    health = connector.health()
    assert isinstance(health, SourceHealth)
    assert health.status == "healthy"


# --- behavior -------------------------------------------------------------


def test_non_colorado_query_returns_nothing(connector: ColoradoOpenDataConnector) -> None:
    assert connector.search(ConnectorQuery(name="KYLDERON", state="TX")) == []


def test_fetch_returns_full_record_shape(connector: ColoradoOpenDataConnector) -> None:
    ref = SourceRef(source_name="colorado_sos_opendata", state="CO", reg_id="20251665680")
    record = connector.fetch(ref)
    assert isinstance(record, RawRecord)
    assert record.response_code == 200
    assert record.raw["legal_name"] == "KYLDERON MIST VALLEY LLC"
    assert record.raw["state"] == "CO"
    assert record.raw["registered_agent"]["name"] == "Registered Agents Inc"


def test_fetch_unknown_id_is_404(connector: ColoradoOpenDataConnector) -> None:
    ref = SourceRef(source_name="colorado_sos_opendata", state="CO", reg_id="does-not-exist")
    assert connector.fetch(ref).response_code == 404


def test_blank_query_returns_nothing(connector: ColoradoOpenDataConnector) -> None:
    # A name that normalizes to empty must not match every row.
    assert connector.search(ConnectorQuery(name="!!!", state="CO")) == []
