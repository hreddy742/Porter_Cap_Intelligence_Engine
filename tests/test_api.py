"""API tests: end-to-end happy path, validation, and the RBAC permission matrix."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
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
from porter_verify.db.models import CoBusinessEntity, CtBusinessEntity, OrBusinessEntity
from porter_verify.services.evidence import EvidenceStore


def _headers(role: str, email: str | None = None) -> dict[str, str]:
    return {"X-User-Email": email or f"{role}@portercap.net", "X-User-Role": role}


def _verify_and_wait(
    client: TestClient, name: str, state: str | None = None, role: str = "sales"
) -> tuple[str, dict]:
    """POST /verify then poll the run once. (TestClient runs background tasks before
    returning, so the run is already terminal here.) Returns (run_id, run dict)."""

    resp = client.post("/verify", json={"name": name, "state": state}, headers=_headers(role))
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]
    run = client.get(f"/runs/{run_id}", headers=_headers(role)).json()["run"]
    return run_id, run


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


def test_local_127_origin_passes_cors_preflight(client: TestClient) -> None:
    resp = client.options(
        "/verify",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-user-email,x-user-role",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


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
    _run_id, run = _verify_and_wait(client, "Acme Logistics LLC", "TX")
    assert run["verification_status"] == "verified"
    company_id = run["company_id"]
    assert company_id is not None

    search = client.get("/companies", params={"q": "Acme"}, headers=_headers("sales"))
    assert search.status_code == 200
    assert any(r["id"] == company_id for r in search.json()["results"])

    profile = client.get(f"/companies/{company_id}/profile", headers=_headers("sales"))
    assert profile.status_code == 200
    assert profile.json()["registrations"][0]["status_normalized"] == "active"


def test_verify_validation_error(client: TestClient) -> None:
    resp = client.post("/verify", json={"name": ""}, headers=_headers("sales"))
    assert resp.status_code == 422


# --- recent business feed -------------------------------------------------


def test_recent_businesses_filter_only_by_state_and_date(
    client: TestClient,
) -> None:
    today = date.today()
    rows = [
        CoBusinessEntity(
            entity_id="CO-RECENT-1",
            entity_name="Front Range Trucking LLC",
            normalized_name="front range trucking",
            status_raw="Good Standing",
            entity_type="DLLC",
            formation_date=today - timedelta(days=2),
            jurisdiction="CO",
            officers=[],
            raw={},
        ),
        CoBusinessEntity(
            entity_id="CO-NONPROFIT",
            entity_name="Front Range Trucking Foundation",
            normalized_name="front range trucking foundation",
            status_raw="Good Standing",
            entity_type="DNC",
            formation_date=today - timedelta(days=2),
            jurisdiction="CO",
            officers=[],
            raw={},
        ),
        CoBusinessEntity(
            entity_id="CO-FOREIGN",
            entity_name="Foreign Trucking LLC",
            normalized_name="foreign trucking",
            status_raw="Good Standing",
            entity_type="FLLC",
            formation_date=today - timedelta(days=2),
            jurisdiction="DE",
            officers=[],
            raw={},
        ),
        CoBusinessEntity(
            entity_id="CO-INACTIVE",
            entity_name="Inactive Trucking LLC",
            normalized_name="inactive trucking",
            status_raw="Voluntarily Dissolved",
            entity_type="DLLC",
            formation_date=today - timedelta(days=2),
            jurisdiction="CO",
            officers=[],
            raw={},
        ),
    ]
    with client.app.state.session_factory() as session:
        session.add_all(rows)
        session.commit()

    params = {
        "states": "CO",
        "formed_from": (today - timedelta(days=7)).isoformat(),
        "formed_to": today.isoformat(),
    }
    response = client.get("/recent-businesses", params=params, headers=_headers("sales"))

    assert response.status_code == 200
    body = response.json()
    assert {item["entity_id"] for item in body["results"]} == {
        "CO-RECENT-1",
        "CO-NONPROFIT",
        "CO-FOREIGN",
        "CO-INACTIVE",
    }
    eligible = next(item for item in body["results"] if item["entity_id"] == "CO-RECENT-1")
    assert eligible["source_record_url"].endswith("?entityid=CO-RECENT-1")

    detail = client.get(
        "/recent-businesses/CO/CO-RECENT-1",
        headers=_headers("sales"),
    )
    assert detail.status_code == 200
    assert detail.json()["legal_name"] == "Front Range Trucking LLC"

def test_recent_connecticut_signals_use_official_citizenship(
    client: TestClient,
) -> None:
    today = date.today()
    rows = [
        CtBusinessEntity(
            entity_id="CT-DOMESTIC",
            entity_name="Domestic Company LLC",
            normalized_name="domestic company",
            status_raw="Active",
            entity_type="LLC",
            formation_date=today,
            jurisdiction=None,
            officers=[],
            raw={"citizenship": "Domestic", "formation_place": "Connecticut"},
        ),
        CtBusinessEntity(
            entity_id="CT-FOREIGN",
            entity_name="Foreign Company LLC",
            normalized_name="foreign company",
            status_raw="Active",
            entity_type="LLC",
            formation_date=today,
            jurisdiction=None,
            officers=[],
            raw={"citizenship": "Foreign"},
        ),
    ]
    with client.app.state.session_factory() as session:
        session.add_all(rows)
        session.commit()

    response = client.get(
        "/recent-businesses",
        params={
            "states": "CT",
            "formed_from": today.isoformat(),
            "formed_to": today.isoformat(),
        },
        headers=_headers("sales"),
    )

    assert response.status_code == 200
    results = {item["entity_id"]: item for item in response.json()["results"]}
    assert set(results) == {"CT-DOMESTIC", "CT-FOREIGN"}
    assert results["CT-DOMESTIC"]["domestic_signal"] is True
    assert results["CT-DOMESTIC"]["jurisdiction"] == "Connecticut"
    assert results["CT-FOREIGN"]["domestic_signal"] is False


def test_recent_oregon_source_link_targets_exact_open_data_record(client: TestClient) -> None:
    today = date.today()
    with client.app.state.session_factory() as session:
        session.add(
            OrBusinessEntity(
                entity_id="OR-RECENT-1",
                entity_name="Oregon Company LLC",
                normalized_name="oregon company",
                status_raw="Active",
                entity_type="DOMESTIC LIMITED LIABILITY COMPANY",
                formation_date=today,
                jurisdiction="OR",
                source_record_url="http://egov.example/legacy-link",
                officers=[],
                raw={},
            )
        )
        session.commit()

    response = client.get(
        "/recent-businesses",
        params={
            "states": "OR",
            "formed_from": today.isoformat(),
            "formed_to": today.isoformat(),
        },
        headers=_headers("sales"),
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["source_record_url"].endswith(
        "?registry_number=OR-RECENT-1"
    )


def test_verify_is_async_pending_then_completes(client: TestClient) -> None:
    resp = client.post(
        "/verify", json={"name": "Acme Logistics LLC", "state": "TX"}, headers=_headers("sales")
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["run_status"] == "pending"
    assert body["company_id"] is None  # result not ready in the immediate response

    run = client.get(f"/runs/{body['run_id']}", headers=_headers("sales")).json()["run"]
    assert run["status"] == "completed"
    assert run["verification_status"] == "verified"
    assert run["company_id"] is not None


# --- field-level access on PII (officers) ---------------------------------


def test_officers_hidden_from_sales_shown_to_underwriter(client: TestClient) -> None:
    _run_id, run = _verify_and_wait(client, "Acme Logistics LLC", "TX")
    company_id = run["company_id"]

    sales_view = client.get(f"/companies/{company_id}/profile", headers=_headers("sales"))
    assert sales_view.json()["officers"] == []

    uw_view = client.get(f"/companies/{company_id}/profile", headers=_headers("underwriter"))
    assert len(uw_view.json()["officers"]) >= 1


def test_registered_agent_surfaced_with_address_masking(client: TestClient) -> None:
    _run_id, run = _verify_and_wait(client, "Acme Logistics LLC", "TX")
    company_id = run["company_id"]

    # Agent name is public record and shown to everyone (incl. sales).
    sales = client.get(f"/companies/{company_id}/profile", headers=_headers("sales")).json()
    assert len(sales["agents"]) >= 1
    assert sales["agents"][0]["agent_name"] == "Jane Roe"
    assert sales["agents"][0]["agent_address"] is None  # PII-adjacent: masked for sales

    # Underwriter (sensitive role) sees the agent address.
    uw = client.get(f"/companies/{company_id}/profile", headers=_headers("underwriter")).json()
    assert uw["agents"][0]["agent_address"] is not None


# --- evidence (sensitive read) --------------------------------------------


def test_evidence_restricted_then_allowed(client: TestClient) -> None:
    _run_id, run = _verify_and_wait(client, "Acme Logistics LLC", "TX")
    company_id = run["company_id"]

    assert (
        client.get(f"/companies/{company_id}/evidence", headers=_headers("sales")).status_code
        == 403
    )
    ok = client.get(f"/companies/{company_id}/evidence", headers=_headers("underwriter"))
    assert ok.status_code == 200
    assert len(ok.json()) >= 1


# --- UCC search coverage --------------------------------------------------


def test_ucc_search_order_permission_and_profile_visibility(client: TestClient) -> None:
    _run_id, run = _verify_and_wait(client, "Acme Logistics LLC", "TX")
    company_id = run["company_id"]
    payload = {"state": "tx"}

    forbidden = client.post(
        f"/companies/{company_id}/ucc-searches",
        json=payload,
        headers=_headers("sales"),
    )
    assert forbidden.status_code == 403

    created = client.post(
        f"/companies/{company_id}/ucc-searches",
        json=payload,
        headers=_headers("underwriter"),
    )
    assert created.status_code == 201
    order = created.json()
    assert order["search_name"] == "Acme Logistics LLC"
    assert order["state"] == "TX"
    assert order["status"] == "pending"
    assert order["outcome"] is None

    duplicate = client.post(
        f"/companies/{company_id}/ucc-searches",
        json=payload,
        headers=_headers("underwriter"),
    )
    assert duplicate.status_code == 409

    sales_profile = client.get(
        f"/companies/{company_id}/profile", headers=_headers("sales")
    ).json()
    assert sales_profile["ucc_searches"] == []

    underwriter_profile = client.get(
        f"/companies/{company_id}/profile", headers=_headers("underwriter")
    ).json()
    assert [item["id"] for item in underwriter_profile["ucc_searches"]] == [order["id"]]


def test_ucc_search_completion_requires_source_and_is_immutable(client: TestClient) -> None:
    _run_id, run = _verify_and_wait(client, "Acme Logistics LLC", "TX")
    company_id = run["company_id"]
    order = client.post(
        f"/companies/{company_id}/ucc-searches",
        json={"state": "TX"},
        headers=_headers("underwriter"),
    ).json()

    missing_source = client.post(
        f"/ucc-searches/{order['id']}/complete",
        json={"outcome": "no_matching_filings"},
        headers=_headers("underwriter"),
    )
    assert missing_source.status_code == 422

    completed = client.post(
        f"/ucc-searches/{order['id']}/complete",
        json={
            "outcome": "no_matching_filings",
            "source_url": "https://direct.sos.state.tx.us/",
            "notes": "Exact legal name searched.",
        },
        headers=_headers("underwriter"),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"] is not None

    repeated = client.post(
        f"/ucc-searches/{order['id']}/complete",
        json={
            "outcome": "filings_found",
            "source_url": "https://direct.sos.state.tx.us/",
        },
        headers=_headers("underwriter"),
    )
    assert repeated.status_code == 409


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


def test_admin_can_govern_source_and_ops_can_read_policy(client: TestClient) -> None:
    client.post(
        "/verify", json={"name": "Acme Logistics LLC", "state": "TX"}, headers=_headers("ops")
    )
    payload = {
        "acquisition_method": "vendor",
        "legal_review_status": "approved",
        "allowed_purposes": ["business_verification", "lead_qualification"],
        "retention_days": 365,
        "freshness_sla_hours": 24,
        "terms_url": "https://vendor.example/terms",
        "owner": "data-ops@portercap.net",
    }

    forbidden = client.put(
        "/sources/mock_vendor/policy", json=payload, headers=_headers("ops")
    )
    assert forbidden.status_code == 403

    updated = client.put(
        "/sources/mock_vendor/policy", json=payload, headers=_headers("admin")
    )
    assert updated.status_code == 200
    assert updated.json()["approved_by"] == "admin@portercap.net"

    health = client.get("/sources/health", headers=_headers("ops")).json()
    source = next(item for item in health if item["name"] == "mock_vendor")
    assert source["policy"]["allowed_purposes"] == [
        "business_verification",
        "lead_qualification",
    ]
    assert source["cost_per_lookup"] == 0.0


def test_source_policy_unknown_source_returns_404(client: TestClient) -> None:
    response = client.put(
        "/sources/missing/policy",
        json={
            "acquisition_method": "vendor",
            "legal_review_status": "pending",
            "allowed_purposes": [],
        },
        headers=_headers("admin"),
    )
    assert response.status_code == 404
