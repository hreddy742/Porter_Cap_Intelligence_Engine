"""Tests for the core ORM models and their constraints.

These verify the data-integrity guarantees the platform depends on: company
deduplication, identifier/registration uniqueness, foreign-key enforcement, and
provenance/timestamp defaults.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porter_verify.db.enums import IdentifierType, RegistrationStatus, RunStatus
from porter_verify.db.models import (
    Company,
    CompanyIdentifier,
    EvidenceItem,
    SourceRegistry,
    VerificationRun,
)
from porter_verify.db.models.verification import EvidenceType


def _make_company(name: str = "Acme Logistics LLC", state: str = "TX") -> Company:
    normalized = name.lower()
    return Company(
        canonical_legal_name=name,
        normalized_name=normalized,
        home_state=state,
        dedupe_key=f"{state}|{normalized}",
    )


def test_company_persists_with_defaults(db_session: Session) -> None:
    company = _make_company()
    db_session.add(company)
    db_session.commit()

    assert isinstance(company.id, uuid.UUID)
    assert company.status_normalized is RegistrationStatus.UNKNOWN
    assert company.created_at is not None
    assert company.updated_at is not None


def test_dedupe_key_is_unique(db_session: Session) -> None:
    db_session.add(_make_company())
    db_session.commit()

    db_session.add(_make_company())  # same name+state => same dedupe_key
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_company_identifier_unique_per_type_and_value(db_session: Session) -> None:
    company = _make_company()
    db_session.add(company)
    db_session.commit()

    db_session.add(
        CompanyIdentifier(
            company_id=company.id, id_type=IdentifierType.STATE_REG, id_value="TX-12345"
        )
    )
    db_session.commit()

    db_session.add(
        CompanyIdentifier(
            company_id=company.id, id_type=IdentifierType.STATE_REG, id_value="TX-12345"
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_foreign_key_is_enforced(db_session: Session) -> None:
    # An identifier pointing at a non-existent company must be rejected.
    db_session.add(
        CompanyIdentifier(company_id=uuid.uuid4(), id_type=IdentifierType.UEI, id_value="ABC123")
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_status_enum_round_trips(db_session: Session) -> None:
    company = _make_company()
    company.status_normalized = RegistrationStatus.ACTIVE
    db_session.add(company)
    db_session.commit()
    db_session.expire_all()

    reloaded = db_session.get(Company, company.id)
    assert reloaded is not None
    assert reloaded.status_normalized is RegistrationStatus.ACTIVE


def test_evidence_item_links_to_run(db_session: Session) -> None:
    source = SourceRegistry(name="mock", capabilities=["entity"], states=[])
    db_session.add(source)
    db_session.commit()

    run = VerificationRun(status=RunStatus.COMPLETED)
    db_session.add(run)
    db_session.commit()

    evidence = EvidenceItem(
        verification_run_id=run.id,
        type=EvidenceType.RAW_JSON,
        storage_uri="file://evidence/abc.json",
        sha256="0" * 64,
    )
    db_session.add(evidence)
    db_session.commit()

    assert evidence.captured_at is not None
    assert run.evidence[0].id == evidence.id
