"""Tests for the async background execution path (Phase A)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from porter_verify.connectors.base import ConnectorQuery, ConnectorRegistry, SourceHealth
from porter_verify.db import models  # noqa: F401
from porter_verify.db.base import Base
from porter_verify.db.enums import RunStatus
from porter_verify.db.models import ErrorLog, VerificationRun
from porter_verify.services.evidence import EvidenceStore
from porter_verify.workers.verify_flow import create_pending_run, run_in_background


class _ExplodingConnector:
    """A connector whose search raises an unexpected (non-outage) error."""

    name = "exploder"
    capabilities = {"status"}
    states: set[str] = set()

    def search(self, query: ConnectorQuery):  # noqa: ANN201
        raise RuntimeError("boom")

    def fetch(self, ref):  # noqa: ANN001, ANN201
        raise RuntimeError("boom")

    def health(self) -> SourceHealth:
        return SourceHealth(status="healthy")


@pytest.fixture
def setup(tmp_path: Path) -> Iterator[tuple]:
    engine: Engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record):  # noqa: ANN001
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    store = EvidenceStore(tmp_path / "evidence")
    yield factory, store
    engine.dispose()


def test_background_crash_marks_run_failed_with_error_log(setup) -> None:
    factory, store = setup
    registry = ConnectorRegistry()
    registry.register(_ExplodingConnector())

    with factory() as session:
        run = create_pending_run(session, actor="dana@portercap.net")
        run_id = run.id
        assert run.status is RunStatus.PENDING

    # Should never raise, even though the connector explodes.
    run_in_background(
        run_id=run_id,
        name="Anything",
        state=None,
        actor="dana@portercap.net",
        session_factory=factory,
        registry=registry,
        evidence_store=store,
    )

    with factory() as session:
        run = session.get(VerificationRun, run_id)
        assert run is not None
        assert run.status is RunStatus.FAILED
        assert run.finished_at is not None
        errors = list(session.scalars(select(ErrorLog).where(ErrorLog.run_id == run_id)))
        assert any(e.error_type == "execution_error" for e in errors)


def test_create_pending_run_audits_with_run_id(setup) -> None:
    from porter_verify.db.models import AuditLog

    factory, _store = setup
    with factory() as session:
        run = create_pending_run(session, actor="dana@portercap.net")
        entry = session.scalars(select(AuditLog).where(AuditLog.action == "run.created")).one()
        # The fix: audit links to the real run id, not None.
        assert entry.entity_id == str(run.id)
