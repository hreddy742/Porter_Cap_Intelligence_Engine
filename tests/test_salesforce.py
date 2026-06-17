"""Tests for the Salesforce integration boundary (foundation)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from porter_verify.db.enums import RegistrationStatus, SyncStatus
from porter_verify.services.companies import upsert_company
from porter_verify.services.salesforce import (
    SalesforceNotConfiguredError,
    build_field_mapping,
    record_sync,
)


class _MockSalesforceClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, str, dict]] = []

    def upsert(self, sf_object: str, sf_record_id: str, fields: dict) -> None:
        if self.fail:
            raise RuntimeError("SF API error")
        self.calls.append((sf_object, sf_record_id, fields))


def _company(session: Session):
    return upsert_company(
        session,
        legal_name="Acme Logistics LLC",
        home_state="TX",
        status=RegistrationStatus.ACTIVE,
    )


def test_sync_refuses_without_client(db_session: Session) -> None:
    company = _company(db_session)
    with pytest.raises(SalesforceNotConfiguredError):
        record_sync(
            db_session,
            company_id=company.id,
            sf_object="Lead",
            sf_record_id="00Q1",
            fields={},
        )


def test_sync_with_client_marks_synced_and_is_idempotent(db_session: Session) -> None:
    company = _company(db_session)
    client = _MockSalesforceClient()
    fields = build_field_mapping(company, verification_status="verified")

    first = record_sync(
        db_session,
        company_id=company.id,
        sf_object="Lead",
        sf_record_id="00Q1",
        fields=fields,
        client=client,
    )
    db_session.commit()
    assert first.sync_status is SyncStatus.SYNCED

    # Re-syncing the same SF record updates the same row (no duplicate).
    second = record_sync(
        db_session,
        company_id=company.id,
        sf_object="Lead",
        sf_record_id="00Q1",
        fields=fields,
        client=client,
    )
    db_session.commit()
    assert second.id == first.id
    assert len(client.calls) == 2


def test_sync_failure_is_recorded(db_session: Session) -> None:
    company = _company(db_session)
    status = record_sync(
        db_session,
        company_id=company.id,
        sf_object="Lead",
        sf_record_id="00Q2",
        fields={},
        client=_MockSalesforceClient(fail=True),
    )
    db_session.commit()
    assert status.sync_status is SyncStatus.FAILED
    assert status.error is not None


def test_field_mapping_only_includes_canonical_facts(db_session: Session) -> None:
    company = _company(db_session)
    mapping = build_field_mapping(company, verification_status="verified")
    assert mapping["LegalName__c"] == "Acme Logistics LLC"
    assert mapping["RegistrationStatus__c"] == "active"
    assert mapping["VerificationStatus__c"] == "verified"
    assert uuid.UUID(str(company.id))  # sanity: company persisted with a UUID id
