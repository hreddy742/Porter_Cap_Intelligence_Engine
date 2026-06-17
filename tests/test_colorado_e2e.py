"""End-to-end: verify a real-shaped Colorado company through the full flow (Feature 4).

Proves the Colorado open-data connector plugs into the existing verify pipeline and
produces a company with registration, evidence, and audit — no mock, no API.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import sessionmaker

from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.connectors.colorado_connector import ColoradoOpenDataConnector
from porter_verify.connectors.colorado_ingest import ingest_co_csv
from porter_verify.db import models  # noqa: F401
from porter_verify.db.base import Base
from porter_verify.db.enums import RegistrationStatus, RunStatus, VerificationStatus
from porter_verify.db.models import BusinessRegistration, Company, EvidenceItem
from porter_verify.services.evidence import EvidenceStore
from porter_verify.workers.verify_flow import run_verification

_CSV = (
    "entityid,entityname,entitystatus,entitytype,entityformdate,principalcity,"
    "principalstate,agentlastname,agentorganizationname\n"
    "20251665680,KYLDERON MIST VALLEY LLC,Good Standing,DLLC,2024-06-16T00:00:00.000,"
    "Delta,CO,,Registered Agents Inc\n"
    '19871342214,"SOUTHWEST CONTRACTING LLC",Delinquent,DLLC,1978-02-28T00:00:00.000,'
    "Cortez,CO,Franchini,\n"
)


@pytest.fixture
def setup(tmp_path: Path):
    # File-based SQLite (not in-memory): the flow and the connector use separate
    # sessions/connections, just like production. In-memory + StaticPool would force
    # them to share one connection and break transaction isolation.
    engine: Engine = create_engine(
        f"sqlite:///{tmp_path / 'e2e.sqlite3'}", connect_args={"check_same_thread": False}
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

    registry = ConnectorRegistry()
    registry.register(ColoradoOpenDataConnector(factory))
    store = EvidenceStore(tmp_path / "evidence")
    yield factory, registry, store
    engine.dispose()


def test_verify_active_colorado_company(setup) -> None:
    factory, registry, store = setup
    with factory() as session:
        outcome = run_verification(
            session,
            registry=registry,
            evidence_store=store,
            name="KYLDERON MIST VALLEY LLC",
            state="CO",
        )

    assert outcome.run_status is RunStatus.COMPLETED
    assert outcome.verification_status is VerificationStatus.VERIFIED
    assert outcome.company_id is not None

    with factory() as session:
        company = session.get(Company, outcome.company_id)
        assert company is not None
        assert company.home_state == "CO"
        assert company.status_normalized is RegistrationStatus.ACTIVE  # "Good Standing" -> active
        reg = session.scalars(select(BusinessRegistration)).first()
        assert reg is not None and reg.state == "CO"
        assert session.scalars(select(EvidenceItem)).first() is not None


def test_verify_delinquent_colorado_company_not_eligible(setup) -> None:
    factory, registry, store = setup
    with factory() as session:
        outcome = run_verification(
            session,
            registry=registry,
            evidence_store=store,
            name="SOUTHWEST CONTRACTING LLC",
            state="CO",
        )
    assert outcome.verification_status is VerificationStatus.INACTIVE_NOT_ELIGIBLE


def test_unknown_colorado_name_is_insufficient(setup) -> None:
    factory, registry, store = setup
    with factory() as session:
        outcome = run_verification(
            session,
            registry=registry,
            evidence_store=store,
            name="Totally Made Up Company XYZ",
            state="CO",
        )
    assert outcome.verification_status is VerificationStatus.INSUFFICIENT_EVIDENCE
