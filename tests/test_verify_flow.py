"""End-to-end tests for the verification flow (the core MVP workflow)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.connectors.factory import build_default_registry
from porter_verify.connectors.mock_vendor import MockVendorConnector
from porter_verify.db.enums import RunStatus, VerificationStatus
from porter_verify.db.models import (
    AuditLog,
    BusinessRegistration,
    Company,
    ConfidenceScore,
    ErrorLog,
    EvidenceItem,
    RawSourceEvent,
)
from porter_verify.services.evidence import EvidenceStore
from porter_verify.workers.verify_flow import run_verification


def _store(tmp_path: Path) -> EvidenceStore:
    return EvidenceStore(tmp_path)


def test_verify_active_company_end_to_end(tmp_path: Path, db_session: Session) -> None:
    outcome = run_verification(
        db_session,
        registry=build_default_registry(),
        evidence_store=_store(tmp_path),
        name="Acme Logistics LLC",
        state="TX",
        actor="dana@portercap.net",
    )

    assert outcome.run_status is RunStatus.COMPLETED
    assert outcome.verification_status is VerificationStatus.VERIFIED
    assert outcome.company_id is not None

    # Company persisted with normalized active status.
    company = db_session.get(Company, outcome.company_id)
    assert company is not None
    assert company.canonical_legal_name == "Acme Logistics LLC"

    # Registration, evidence, raw events, scores, and audit all recorded.
    assert db_session.scalars(select(BusinessRegistration)).first() is not None
    assert db_session.scalars(select(EvidenceItem)).first() is not None
    assert len(list(db_session.scalars(select(RawSourceEvent)))) >= 2  # search + fetch
    assert len(list(db_session.scalars(select(ConfidenceScore)))) == 5
    assert db_session.scalars(select(AuditLog)).first() is not None


def test_dissolved_company_is_not_eligible(tmp_path: Path, db_session: Session) -> None:
    outcome = run_verification(
        db_session,
        registry=build_default_registry(),
        evidence_store=_store(tmp_path),
        name="Defunct Holdings LLC",
        state="DE",
    )
    assert outcome.run_status is RunStatus.COMPLETED
    assert outcome.verification_status is VerificationStatus.INACTIVE_NOT_ELIGIBLE


def test_delinquent_company_is_not_eligible(tmp_path: Path, db_session: Session) -> None:
    outcome = run_verification(
        db_session,
        registry=build_default_registry(),
        evidence_store=_store(tmp_path),
        name="Lone Star Freight Co",
        state="TX",
    )
    assert outcome.verification_status is VerificationStatus.INACTIVE_NOT_ELIGIBLE


def test_unknown_company_is_insufficient_evidence(tmp_path: Path, db_session: Session) -> None:
    outcome = run_verification(
        db_session,
        registry=build_default_registry(),
        evidence_store=_store(tmp_path),
        name="Nonexistent Phantom Company",
        state="TX",
    )
    assert outcome.run_status is RunStatus.COMPLETED
    assert outcome.verification_status is VerificationStatus.INSUFFICIENT_EVIDENCE
    assert outcome.company_id is None


def test_low_confidence_no_match_does_not_create_company(
    tmp_path: Path, db_session: Session
) -> None:
    # "Acme" is contained in the fixture name, so a candidate is returned and the
    # fetch succeeds, but name similarity is below the review threshold (NO_MATCH,
    # score ~0.47). A below-threshold, unverified match must NOT be persisted as a
    # canonical company — that would fabricate a record the source never confirmed.
    outcome = run_verification(
        db_session,
        registry=build_default_registry(),
        evidence_store=_store(tmp_path),
        name="Acme",
        state="TX",
    )
    assert outcome.run_status is RunStatus.COMPLETED
    assert outcome.verification_status is VerificationStatus.INSUFFICIENT_EVIDENCE
    assert outcome.company_id is None
    # No canonical company row written for the weak match.
    assert list(db_session.scalars(select(Company))) == []


def test_partial_name_routes_to_review(tmp_path: Path, db_session: Session) -> None:
    # A partial name match is plausible but not exact -> human review, not VERIFIED.
    outcome = run_verification(
        db_session,
        registry=build_default_registry(),
        evidence_store=_store(tmp_path),
        name="Acme Logistics",
        state="TX",
    )
    assert outcome.verification_status is VerificationStatus.NEEDS_REVIEW


def test_source_outage_finishes_without_charge(tmp_path: Path, db_session: Session) -> None:
    registry = ConnectorRegistry()
    registry.register(MockVendorConnector(available=False))

    outcome = run_verification(
        db_session,
        registry=registry,
        evidence_store=_store(tmp_path),
        name="Acme Logistics LLC",
        state="TX",
    )
    assert outcome.run_status is RunStatus.SOURCE_UNAVAILABLE

    error = db_session.scalars(select(ErrorLog)).first()
    assert error is not None
    # No raw source event (= no vendor charge) was recorded for the outage.
    assert db_session.scalars(select(RawSourceEvent)).first() is None


def test_sanctioned_entity_flagged_even_without_registry_record(
    tmp_path: Path, db_session: Session
) -> None:
    # "Sanctioned Trading Company" is in the OFAC fixture but has no mock-vendor record.
    # Before the fix: no search hits => INSUFFICIENT_EVIDENCE (OFAC never ran).
    # After the fix: pre-screen catches the OFAC match before registry lookup => RISK_FLAG.
    outcome = run_verification(
        db_session,
        registry=build_default_registry(),
        evidence_store=_store(tmp_path),
        name="Sanctioned Trading Company",
        state="TX",
    )
    assert outcome.verification_status is VerificationStatus.RISK_FLAG
    assert outcome.company_id is None  # not persisted; sanctioned entities are not clients


def test_verification_is_repeatable_without_duplicate_company(
    tmp_path: Path, db_session: Session
) -> None:
    registry = build_default_registry()
    store = _store(tmp_path)
    first = run_verification(
        db_session, registry=registry, evidence_store=store, name="Acme Logistics LLC", state="TX"
    )
    second = run_verification(
        db_session, registry=registry, evidence_store=store, name="Acme Logistics LLC", state="TX"
    )
    # Same company (dedupe_key), two runs.
    assert first.company_id == second.company_id
    assert len(list(db_session.scalars(select(Company)))) == 1
