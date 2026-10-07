"""Salesforce integration boundary (foundation for Phase 3).

This is the seam where Salesforce sync will plug in. It is intentionally inert by
default: ``record_sync`` REFUSES to push unless an explicit, approved client is
provided. No Porter data leaves the system until credentials, field mappings, and
an approval flow are configured (plan Phase 7 / §7.13).

The ``SalesforceClient`` Protocol lets us build and test the whole flow against a
mock now, then drop in a real REST/Bulk client later with zero changes upstream.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.db.base import utcnow
from porter_verify.db.enums import SyncStatus
from porter_verify.db.models import Company, SalesforceSyncStatus
from porter_verify.services.audit import record_audit


class SalesforceNotConfiguredError(RuntimeError):
    """Raised when a sync is attempted without an approved, configured client."""


class SalesforceClient(Protocol):
    """Minimal upsert contract a real Salesforce client must satisfy."""

    def upsert(self, sf_object: str, sf_record_id: str, fields: dict) -> None: ...


def build_field_mapping(company: Company, verification_status: str | None) -> dict:
    """Map a verified company to the Salesforce fields Porter writes back.

    Conservative: only canonical, evidence-backed facts. Extend once the SF schema
    mapping is confirmed with Porter's Salesforce admin.
    """

    return {
        "LegalName__c": company.canonical_legal_name,
        "RegistrationStatus__c": company.status_normalized.value,
        "VerificationStatus__c": verification_status,
        "HomeState__c": company.home_state,
    }


def record_sync(
    session: Session,
    *,
    company_id: uuid.UUID,
    sf_object: str,
    sf_record_id: str,
    fields: dict,
    actor: str = "system",
    client: SalesforceClient | None = None,
) -> SalesforceSyncStatus:
    """Push fields to Salesforce (idempotently) and record the sync status.

    With ``client=None`` this raises — the safe default that guarantees nothing is
    sent to Salesforce until an approved client is explicitly wired in.
    """

    if client is None:
        raise SalesforceNotConfiguredError(
            "Salesforce sync is not configured. Provide an approved client to enable it."
        )

    status = session.scalar(
        select(SalesforceSyncStatus).where(
            SalesforceSyncStatus.sf_object == sf_object,
            SalesforceSyncStatus.sf_record_id == sf_record_id,
        )
    )
    if status is None:
        status = SalesforceSyncStatus(
            company_id=company_id, sf_object=sf_object, sf_record_id=sf_record_id
        )
        session.add(status)

    try:
        client.upsert(sf_object, sf_record_id, fields)
        status.sync_status = SyncStatus.SYNCED
        status.last_synced_at = utcnow()
        status.error = None
    except Exception as exc:  # noqa: BLE001 — record any client failure as a sync error
        status.sync_status = SyncStatus.FAILED
        status.error = str(exc)

    record_audit(
        session,
        actor=actor,
        action="salesforce.sync",
        entity_type="company",
        entity_id=str(company_id),
        after={
            "sf_object": sf_object,
            "sf_record_id": sf_record_id,
            "status": status.sync_status.value,
        },
    )
    session.flush()
    return status
