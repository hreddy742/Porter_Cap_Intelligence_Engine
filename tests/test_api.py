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
from porter_verify.api.security import _build_key_map
from porter_verify.config import get_settings
from porter_verify.connectors.factory import build_default_registry
from porter_verify.db import models  # noqa: F401  (register tables)
from porter_verify.db.base import Base
from porter_verify.db.models import (
    AlBusinessEntity,
    CoBusinessEntity,
    CtBusinessEntity,
    OrBusinessEntity,
)
from porter_verify.services.evidence import EvidenceStore
from porter_verify.services.ofac import get_ofac_metadata_by_name
from porter_verify.services.screening import get_sanctions_list


_TEST_API_KEYS = {role: f"sk-test-{role}" for role in ("sales", "underwriter", "ops", "admin", "compliance")}


def _headers(role: str, email: str | None = None) -> dict[str, str]:
    del email  # identity now comes from the server-side key map, not the caller
    return {"Authorization": f"Bearer {_TEST_API_KEYS[role]}"}


@pytest.fixture(autouse=True)
def _configure_test_api_keys(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    raw = ",".join(f"{role}@portercap.net:{role}:{key}" for role, key in _TEST_API_KEYS.items())
    monkeypatch.setenv("PORTER_API_KEYS", raw)
    get_settings.cache_clear()
    _build_key_map.cache_clear()
    yield
    get_settings.cache_clear()
    _build_key_map.cache_clear()


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
    body = resp.json()
    assert body["status"] == "ok"
    assert "AL" in body["record_counts"]
    assert "AL" in body["last_refresh_timestamps"]


def test_local_127_origin_passes_cors_preflight(client: TestClient) -> None:
    resp = client.options(
        "/verify",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
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
        headers={"Authorization": "Bearer sk-not-a-real-key"},
    )
    assert resp.status_code == 401


def test_ofac_requires_auth(client: TestClient) -> None:
    resp = client.get("/ofac", params={"company": "Acme Logistics LLC"})
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


def test_get_verify_searches_alabama_registry_and_ofac(client: TestClient) -> None:
    with client.app.state.session_factory() as session:
        session.add(
            AlBusinessEntity(
                entity_id="000123456",
                entity_name="Bama Freight LLC",
                normalized_name="bama freight llc",
                status_raw="Exists",
                entity_type="Domestic Limited Liability Company",
                formation_date=date(2026, 6, 1),
                principal_address="100 Commerce St",
                mailing_address=None,
                jurisdiction="AL",
                source_record_url="https://arc-sos.state.al.us/cgi/corpdetail.mbr/detail?corp=000123456",
                agent_name="Jane Agent",
                agent_address=None,
                officers=[],
                raw={},
            )
        )
        session.commit()

    resp = client.get(
        "/verify",
        params={"company": "Bama Freight LLC", "state": "AL"},
        headers=_headers("sales"),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["confidence"] == 1.0
    assert body["status"] == "Exists"
    assert body["entity_type"] == "Domestic Limited Liability Company"
    assert body["formation_date"] == "2026-06-01"
    assert body["address"] == "100 Commerce St"
    assert body["ofac_clear"] is True


def test_get_verify_returns_not_verified_for_missing_registry_match(client: TestClient) -> None:
    resp = client.get(
        "/verify",
        params={"company": "Missing Company LLC", "state": "AL"},
        headers=_headers("sales"),
    )

    assert resp.status_code == 200
    assert resp.json()["verified"] is False


def test_ofac_endpoint_returns_clear_for_non_hit(client: TestClient) -> None:
    resp = client.get(
        "/ofac",
        params={"company": "Acme Logistics LLC"},
        headers=_headers("compliance"),
    )

    assert resp.status_code == 200
    assert resp.json() == {"company": "Acme Logistics LLC", "clear": True, "match": None}


def test_ofac_endpoint_returns_match_with_program(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sdn = tmp_path / "sdn.csv"
    sdn.write_text(
        '306,"BANCO NACIONAL DE CUBA","aka BNC ","CUBA",-0- ,-0- ,-0- ,-0-\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("PORTER_OFAC_SDN_PATH", str(sdn))
    get_settings.cache_clear()
    get_sanctions_list.cache_clear()
    get_ofac_metadata_by_name.cache_clear()
    try:
        resp = client.get(
            "/ofac",
            params={"company": "Banco Nacional de Cuba"},
            headers=_headers("sales"),
        )
    finally:
        get_settings.cache_clear()
        get_sanctions_list.cache_clear()
        get_ofac_metadata_by_name.cache_clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["clear"] is False
    assert body["match"]["match_name"] == "BANCO NACIONAL DE CUBA"
    assert body["match"]["match_type"] == "exact"
    assert body["match"]["program"] == "CUBA"


def test_ofac_endpoint_returns_alias_match_with_program(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sdn = tmp_path / "sdn.csv"
    alt = tmp_path / "alt.csv"
    sdn.write_text(
        '306,"BANCO NACIONAL DE CUBA","aka BNC ","CUBA",-0- ,-0- ,-0- ,-0-\n',
        encoding="utf-8",
    )
    alt.write_text('306,1,"aka","BNC",-0-\n', encoding="utf-8")
    monkeypatch.setenv("PORTER_OFAC_SDN_PATH", str(sdn))
    monkeypatch.setenv("PORTER_OFAC_ALT_PATH", str(alt))
    get_settings.cache_clear()
    get_sanctions_list.cache_clear()
    get_ofac_metadata_by_name.cache_clear()
    try:
        resp = client.get(
            "/ofac",
            params={"company": "BNC"},
            headers=_headers("sales"),
        )
    finally:
        get_settings.cache_clear()
        get_sanctions_list.cache_clear()
        get_ofac_metadata_by_name.cache_clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["clear"] is False
    assert body["match"]["match_name"] == "BNC"
    assert body["match"]["match_type"] == "alias"
    assert body["match"]["program"] == "CUBA"


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
    assert body["pagination"] == {
        "page": 1,
        "page_size": 50,
        "total": 4,
        "total_pages": 1,
    }

    detail = client.get(
        "/recent-businesses/CO/CO-RECENT-1",
        headers=_headers("sales"),
    )
    assert detail.status_code == 200
    assert detail.json()["legal_name"] == "Front Range Trucking LLC"


def test_recent_businesses_search_pagination_and_sorting(client: TestClient) -> None:
    today = date.today()
    rows = [
        CoBusinessEntity(
            entity_id="CO-SEARCH-100",
            entity_name="Alpha Freight LLC",
            normalized_name="alpha freight",
            status_raw="Good Standing",
            entity_type="DLLC",
            formation_date=today - timedelta(days=1),
            jurisdiction="CO",
            officers=[],
            raw={},
        ),
        CoBusinessEntity(
            entity_id="CO-SEARCH-200",
            entity_name="Beta Freight LLC",
            normalized_name="beta freight",
            status_raw="Good Standing",
            entity_type="DLLC",
            formation_date=today - timedelta(days=2),
            jurisdiction="CO",
            officers=[],
            raw={},
        ),
        CtBusinessEntity(
            entity_id="CT-SEARCH-300",
            entity_name="Gamma Freight LLC",
            normalized_name="gamma freight",
            status_raw="Active",
            entity_type="LLC",
            formation_date=today - timedelta(days=3),
            jurisdiction="CT",
            officers=[],
            raw={"citizenship": "Domestic"},
        ),
    ]
    with client.app.state.session_factory() as session:
        session.add_all(rows)
        session.commit()

    common = {
        "states": "CO,CT",
        "formed_from": (today - timedelta(days=7)).isoformat(),
        "formed_to": today.isoformat(),
        "q": "freight",
        "sort_by": "legal_name",
        "sort_order": "asc",
        "page_size": 2,
    }
    first = client.get(
        "/recent-businesses",
        params={**common, "page": 1},
        headers=_headers("sales"),
    )
    second = client.get(
        "/recent-businesses",
        params={**common, "page": 2},
        headers=_headers("sales"),
    )

    assert first.status_code == 200
    assert [item["legal_name"] for item in first.json()["results"]] == [
        "Alpha Freight LLC",
        "Beta Freight LLC",
    ]
    assert first.json()["pagination"] == {
        "page": 1,
        "page_size": 2,
        "total": 3,
        "total_pages": 2,
    }
    assert [item["legal_name"] for item in second.json()["results"]] == [
        "Gamma Freight LLC"
    ]

    by_id = client.get(
        "/recent-businesses",
        params={**common, "q": "SEARCH-300"},
        headers=_headers("sales"),
    )
    assert [item["entity_id"] for item in by_id.json()["results"]] == [
        "CT-SEARCH-300"
    ]
    assert by_id.json()["filters"]["q"] == "SEARCH-300"

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
