"""Tests for UCC filing intelligence."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from porter_verify.api.app import create_app
from porter_verify.api.routers import ucc as ucc_router
from porter_verify.api.security import _build_key_map
from porter_verify.config import get_settings
from porter_verify.connectors.idaho_ucc import IdahoUccSearchResult
from porter_verify.connectors.washington_ucc import ingest_washington_ucc_file
from porter_verify.db.base import utcnow
from porter_verify.db.models import KnownFactor, UccFiling
from porter_verify.services.ucc_intelligence import (
    classify_lender,
    detect_exit_signals,
    find_ucc_filings,
    normalize_ucc_name,
    record_refresh_log,
    seed_known_factors,
)


_TEST_API_KEYS = {role: f"sk-test-{role}" for role in ("sales", "underwriter", "ops", "admin", "compliance")}


def _headers(role: str = "ops") -> dict[str, str]:
    return {"Authorization": f"Bearer {_TEST_API_KEYS[role]}"}


@pytest.fixture(autouse=True)
def _configure_test_api_keys(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    raw = ",".join(f"{role}@porter.local:{role}:{key}" for role, key in _TEST_API_KEYS.items())
    monkeypatch.setenv("PORTER_API_KEYS", raw)
    get_settings.cache_clear()
    _build_key_map.cache_clear()
    yield
    get_settings.cache_clear()
    _build_key_map.cache_clear()


@pytest.fixture
def client(db_engine) -> Iterator[TestClient]:  # noqa: ANN001
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    app = create_app(session_factory=factory)
    with TestClient(app) as test_client:
        yield test_client


def _filing(
    filing_id: str,
    *,
    debtor: str = "Acme Logistics LLC",
    secured_party: str = "Triumph Business Capital",
    filing_type: str = "UCC1",
    filing_date: date | None = None,
    termination_date: date | None = None,
    lender_type: str = "FACTOR",
    status: str = "ACTIVE",
    state: str = "CT",
) -> UccFiling:
    filing_date = filing_date or date.today() - timedelta(days=60)
    return UccFiling(
        id=f"{state}:{filing_id}",
        filing_id=filing_id,
        state=state,
        filing_type=filing_type,
        debtor_name=debtor,
        debtor_normalized=normalize_ucc_name(debtor),
        secured_party_name=secured_party,
        secured_party_normalized=normalize_ucc_name(secured_party),
        filing_date=filing_date,
        termination_date=termination_date,
        status=status,
        lender_type=lender_type,
        is_factoring_related=lender_type == "FACTOR",
        is_mca_related=lender_type == "MCA",
        source_state=state,
    )


def test_lender_classification_prefers_known_factor(db_session: Session) -> None:
    result = classify_lender(db_session, "Triumph Business Capital")

    assert result.lender_type == "FACTOR"
    assert result.is_factoring_related is True
    assert result.is_mca_related is False


def test_lender_classification_mca_is_suppressed_not_factor(db_session: Session) -> None:
    result = classify_lender(db_session, "Rapid Advance Funding Solutions")

    assert result.lender_type == "MCA"
    assert result.is_factoring_related is False
    assert result.is_mca_related is True


def test_exit_signal_created_for_factor_without_replacement(db_session: Session) -> None:
    today = date(2026, 7, 1)
    db_session.add(_filing("ucc1", filing_date=today - timedelta(days=80)))
    db_session.add(
        _filing(
            "ucc3",
            filing_type="UCC3",
            filing_date=today - timedelta(days=10),
            termination_date=today - timedelta(days=10),
            status="TERMINATED",
        )
    )
    db_session.commit()

    assert detect_exit_signals(db_session, today=today) == 1


def test_exit_signal_not_created_when_replacement_filed(db_session: Session) -> None:
    today = date(2026, 7, 1)
    db_session.add(_filing("ucc1", filing_date=today - timedelta(days=80)))
    db_session.add(
        _filing(
            "ucc3",
            filing_type="UCC3",
            filing_date=today - timedelta(days=10),
            termination_date=today - timedelta(days=10),
            status="TERMINATED",
        )
    )
    db_session.add(_filing("replacement", secured_party="New Bank", filing_date=today))
    db_session.commit()

    assert detect_exit_signals(db_session, today=today) == 0


def test_washington_ucc_file_ingest_classifies_rows(
    db_session: Session, tmp_path: Path
) -> None:
    path = tmp_path / "wa_ucc.csv"
    path.write_text(
        "filing_id,debtor_name,secured_party_name,filing_type,filing_date,status\n"
        "2026001,Acme Logistics LLC,First National Bank,UCC1,2026-06-01,ACTIVE\n",
        encoding="utf-8",
    )

    assert ingest_washington_ucc_file(db_session, path) == 1
    row = db_session.get(UccFiling, "WA:2026001")
    assert row is not None
    assert row.lender_type == "BANK"


def test_find_ucc_filings_matches_common_suffix_variants(db_session: Session) -> None:
    db_session.add(_filing("suffix-match", debtor="WALMART INC.", state="NJ"))
    db_session.commit()

    rows = find_ucc_filings(db_session, "WALMART", "NJ")

    assert [row.filing_id for row in rows] == ["suffix-match"]


def test_refresh_log_records_run(db_session: Session) -> None:
    row = record_refresh_log(
        db_session,
        state="CT",
        refresh_type="FULL",
        records_added=2,
        records_updated=0,
        started_at=utcnow(),
        status="SUCCESS",
    )

    assert row.status == "SUCCESS"


def test_known_factors_seeded(db_session: Session) -> None:
    seed_known_factors(db_session)

    assert db_session.query(KnownFactor).count() >= 12


def test_ucc_endpoints_and_health(client: TestClient) -> None:
    today = date.today()
    with client.app.state.session_factory() as session:
        session.add(_filing("ucc1", filing_date=today - timedelta(days=80)))
        session.add(
            _filing(
                "ucc3",
                filing_type="UCC3",
                filing_date=today - timedelta(days=10),
                termination_date=today - timedelta(days=10),
                status="TERMINATED",
            )
        )
        session.commit()
        detect_exit_signals(session, today=today)

    lookup = client.get("/ucc", params={"company": "Acme Logistics LLC"}, headers=_headers())
    assert lookup.status_code == 200
    assert lookup.json()["ucc_exit_signal"] is True

    exits = client.get("/ucc/exits", headers=_headers())
    assert exits.status_code == 200
    assert exits.json()[0]["days_since_exit"] == 10

    factors = client.get("/ucc/known-factors", headers=_headers())
    assert factors.status_code == 200
    assert any(item["company_name"] == "Triumph Business Capital" for item in factors.json())

    created = client.post(
        "/ucc/known-factors",
        json={"company_name": "Porter Test Factor", "lender_type": "FACTOR"},
        headers=_headers("ops"),
    )
    assert created.status_code == 201

    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["ucc_filing_count"] >= 2
    assert body["ucc_exit_signals"] >= 1


def test_public_search_endpoint_ingests_supported_state(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_search(company_name: str) -> list[IdahoUccSearchResult]:
        assert company_name == "CONSTRUCTION"
        return [
            IdahoUccSearchResult(
                debtor_name="CONSTRUCTION, INC.",
                filing_number="20102496473",
                secured_party="NORTHWEST FARM CREDIT SERVICES, FLCA - BURLEY, ID",
                status="Active",
                filing_date=date(2010, 12, 8),
                lien_type="Initial",
            )
        ]

    from porter_verify.connectors import idaho_ucc

    monkeypatch.setattr(idaho_ucc, "search_idaho_ucc", fake_search)

    response = client.post(
        "/ucc/public-search",
        json={"company": "CONSTRUCTION", "state": "ID"},
        headers=_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["imported_count"] == 1
    assert body["lookup"]["has_active_ucc"] is True
    assert body["lookup"]["active_filings"][0]["acquisition_method"] == "PUBLIC_SEARCH"


def test_public_search_endpoint_reports_unsupported_state(client: TestClient) -> None:
    response = client.post(
        "/ucc/public-search",
        json={"company": "ACME", "state": "TN"},
        headers=_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is False
    assert body["imported_count"] == 0
    assert "ID" in body["message"]
    assert "not TN" in body["message"]


def test_ucc_coverage_reports_loaded_and_blocked_states(client: TestClient) -> None:
    with client.app.state.session_factory() as session:
        session.add(_filing("co-1", debtor="Front Range LLC", state="CO"))
        record_refresh_log(
            session,
            state="CO",
            refresh_type="FULL",
            records_added=1,
            records_updated=0,
            started_at=utcnow(),
            status="SUCCESS",
        )

    response = client.get("/ucc/coverage", headers=_headers())

    assert response.status_code == 200
    states = {item["state"]: item for item in response.json()["states"]}
    assert states["CO"]["status"] == "bulk_loaded"
    assert states["CO"]["record_count"] == 1
    assert states["CO"]["last_refresh"] is not None
    assert states["ID"]["status"] == "targeted_public_search"
    assert states["IA"]["status"] == "blocked"
    assert states["MI"]["status"] == "targeted_public_search"
    assert states["NJ"]["status"] == "targeted_public_search"
    assert states["IN"]["status"] == "blocked"
    assert states["IN"]["record_count"] == 0
    assert states["TN"]["status"] == "blocked"
    assert states["WV"]["status"] == "blocked"


def test_manual_ucc_search_can_be_created_for_blocked_state(client: TestClient) -> None:
    payload = {
        "company": "Indiana Freight LLC",
        "state": "in",
        "notes": "Indiana public search blocked by CAPTCHA.",
    }

    forbidden = client.post("/ucc/manual-searches", json=payload, headers=_headers("sales"))
    assert forbidden.status_code == 403

    created = client.post("/ucc/manual-searches", json=payload, headers=_headers("underwriter"))

    assert created.status_code == 201
    body = created.json()
    assert body["search_name"] == "Indiana Freight LLC"
    assert body["state"] == "IN"
    assert body["status"] == "pending"
    assert body["notes"] == "Indiana public search blocked by CAPTCHA."

    duplicate = client.post("/ucc/manual-searches", json=payload, headers=_headers("underwriter"))
    assert duplicate.status_code == 409


def test_manual_ucc_search_queue_lists_pending_requests(client: TestClient) -> None:
    payload = {
        "company": "Queue Freight LLC",
        "state": "IN",
        "notes": "Queue smoke test.",
    }
    created = client.post("/ucc/manual-searches", json=payload, headers=_headers("underwriter"))
    assert created.status_code == 201

    forbidden = client.get("/ucc/manual-searches", headers=_headers("sales"))
    assert forbidden.status_code == 403

    queue = client.get("/ucc/manual-searches", headers=_headers("ops"))

    assert queue.status_code == 200
    rows = queue.json()
    assert len(rows) == 1
    assert rows[0]["search_name"] == "Queue Freight LLC"
    assert rows[0]["state"] == "IN"
    assert rows[0]["status"] == "pending"

    completed = client.post(
        f"/ucc-searches/{rows[0]['id']}/complete",
        json={
            "outcome": "no_matching_filings",
            "source_url": "https://bsd.sos.in.gov/PublicUCCSearch",
            "notes": "Official search completed.",
        },
        headers=_headers("underwriter"),
    )
    assert completed.status_code == 200

    after = client.get("/ucc/manual-searches", headers=_headers("ops"))
    assert after.status_code == 200
    assert after.json() == []

    history = client.get(
        "/ucc/manual-searches",
        params={"status": "completed"},
        headers=_headers("ops"),
    )
    assert history.status_code == 200
    completed_rows = history.json()
    assert len(completed_rows) == 1
    assert completed_rows[0]["search_name"] == "Queue Freight LLC"
    assert completed_rows[0]["outcome"] == "no_matching_filings"
    assert completed_rows[0]["source_url"] == "https://bsd.sos.in.gov/PublicUCCSearch"
    assert completed_rows[0]["completed_by_email"] == "underwriter@porter.local"
    assert completed_rows[0]["completed_at"] is not None
