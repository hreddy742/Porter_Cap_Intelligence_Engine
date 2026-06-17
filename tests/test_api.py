"""API tests: end-to-end happy path, validation, and the RBAC permission matrix."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from porter_verify.api.app import create_app
from porter_verify.connectors.factory import build_default_registry
from porter_verify.db import models  # noqa: F401  (register tables)
from porter_verify.db.base import Base
from porter_verify.services.evidence import EvidenceStore


def _headers(role: str, email: str | None = None) -> dict[str, str]:
    return {"X-User-Email": email or f"{role}@portercap.net", "X-User-Role": role}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, _record):  # noqa: ANN001
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app(
        session_factory=factory,
        registry=build_default_registry(),
        evidence_store=EvidenceStore(tmp_path),
    )
    with TestClient(app) as test_client:
        yield test_client


# --- health ---------------------------------------------------------------


def test_health_is_public(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# --- auth boundary --------------------------------------------------------


def test_verify_requires_auth(client: TestClient) -> None:
    resp = client.post("/verify", json={"name": "Acme Logistics LLC", "state": "TX"})
    assert resp.status_code == 401


def test_verify_rejects_unknown_role(client: TestClient) -> None:
    resp = client.post(
        "/verify",
        json={"name": "Acme Logistics LLC", "state": "TX"},
        headers={"X-User-Email": "x@portercap.net", "X-User-Role": "wizard"},
    )
    assert resp.status_code == 401


def test_compliance_cannot_verify(client: TestClient) -> None:
    resp = client.post(
        "/verify",
        json={"name": "Acme Logistics LLC", "state": "TX"},
        headers=_headers("compliance"),
    )
    assert resp.status_code == 403


# --- happy path -----------------------------------------------------------


def test_verify_then_search_and_profile(client: TestClient) -> None:
    verify = client.post(
        "/verify", json={"name": "Acme Logistics LLC", "state": "TX"}, headers=_headers("sales")
    )
    assert verify.status_code == 200
    body = verify.json()
    assert body["verification_status"] == "verified"
    company_id = body["company_id"]

    search = client.get("/companies", params={"q": "Acme"}, headers=_headers("sales"))
    assert search.status_code == 200
    assert any(r["id"] == company_id for r in search.json()["results"])

    profile = client.get(f"/companies/{company_id}/profile", headers=_headers("sales"))
    assert profile.status_code == 200
    assert profile.json()["registrations"][0]["status_normalized"] == "active"


def test_verify_validation_error(client: TestClient) -> None:
    resp = client.post("/verify", json={"name": ""}, headers=_headers("sales"))
    assert resp.status_code == 422


# --- field-level access on PII (officers) ---------------------------------


def test_officers_hidden_from_sales_shown_to_underwriter(client: TestClient) -> None:
    company_id = client.post(
        "/verify", json={"name": "Acme Logistics LLC", "state": "TX"}, headers=_headers("sales")
    ).json()["company_id"]

    sales_view = client.get(f"/companies/{company_id}/profile", headers=_headers("sales"))
    assert sales_view.json()["officers"] == []

    uw_view = client.get(f"/companies/{company_id}/profile", headers=_headers("underwriter"))
    assert len(uw_view.json()["officers"]) >= 1


# --- evidence (sensitive read) --------------------------------------------


def test_evidence_restricted_then_allowed(client: TestClient) -> None:
    company_id = client.post(
        "/verify", json={"name": "Acme Logistics LLC", "state": "TX"}, headers=_headers("sales")
    ).json()["company_id"]

    assert (
        client.get(f"/companies/{company_id}/evidence", headers=_headers("sales")).status_code
        == 403
    )
    ok = client.get(f"/companies/{company_id}/evidence", headers=_headers("underwriter"))
    assert ok.status_code == 200
    assert len(ok.json()) >= 1


# --- review ---------------------------------------------------------------


def test_review_decision_permission_matrix(client: TestClient) -> None:
    run_id = client.post(
        "/verify", json={"name": "Acme Logistics", "state": "TX"}, headers=_headers("sales")
    ).json()["run_id"]

    forbidden = client.post(
        f"/review/{run_id}/decision", json={"decision": "approved"}, headers=_headers("sales")
    )
    assert forbidden.status_code == 403

    ok = client.post(
        f"/review/{run_id}/decision",
        json={"decision": "approved", "reason": "Confirmed legal name."},
        headers=_headers("underwriter"),
    )
    assert ok.status_code == 200
    assert ok.json()["decision"] == "approved"


# --- source health --------------------------------------------------------


def test_source_health_requires_ops_or_admin(client: TestClient) -> None:
    # Run once so a source row exists.
    client.post(
        "/verify", json={"name": "Acme Logistics LLC", "state": "TX"}, headers=_headers("ops")
    )
    assert client.get("/sources/health", headers=_headers("sales")).status_code == 403
    ok = client.get("/sources/health", headers=_headers("ops"))
    assert ok.status_code == 200
    assert any(s["name"] == "mock_vendor" for s in ok.json())
