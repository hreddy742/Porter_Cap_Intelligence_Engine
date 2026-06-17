"""Company repository: read/write the canonical company spine and its children.

All company writes go through here so the dedupe rule (one company per
``dedupe_key``) and provenance (every fact carries a ``source_id``) are enforced in
one place. Upserts never blindly overwrite — they update the canonical record and
add child rows, preserving history via the append-only evidence/run tables.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.db.enums import RegistrationStatus
from porter_verify.db.models import (
    BusinessRegistration,
    Company,
    CompanyOfficer,
    RegisteredAgent,
    SourceRegistry,
)
from porter_verify.services.normalization import dedupe_key, normalize_name


def get_or_create_source(
    session: Session,
    *,
    name: str,
    capabilities: list[str],
    states: list[str],
    cost_per_lookup: float = 0.0,
) -> SourceRegistry:
    """Return the registry row for a source, creating it if absent (idempotent)."""

    existing = session.scalar(select(SourceRegistry).where(SourceRegistry.name == name))
    if existing is not None:
        return existing
    source = SourceRegistry(
        name=name,
        capabilities=capabilities,
        states=states,
        cost_per_lookup=cost_per_lookup,
        health_status="healthy",
    )
    session.add(source)
    session.flush()
    return source


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _age_days(formation: date | None, as_of: date | None = None) -> int | None:
    if formation is None:
        return None
    as_of = as_of or datetime.now().date()
    return (as_of - formation).days


def upsert_company(
    session: Session,
    *,
    legal_name: str,
    home_state: str | None,
    status: RegistrationStatus,
    formation_date: date | None = None,
) -> Company:
    """Create or update the canonical company identified by its dedupe_key."""

    normalized = normalize_name(legal_name)
    key = dedupe_key(home_state, normalized)

    company = session.scalar(select(Company).where(Company.dedupe_key == key))
    if company is None:
        company = Company(
            canonical_legal_name=legal_name,
            normalized_name=normalized,
            home_state=home_state,
            status_normalized=status,
            entity_age_days=_age_days(formation_date),
            dedupe_key=key,
        )
        session.add(company)
    else:
        # Update the canonical status/age; the audit trail + runs preserve history.
        company.status_normalized = status
        if formation_date is not None:
            company.entity_age_days = _age_days(formation_date)
    session.flush()
    return company


def add_registration(
    session: Session,
    *,
    company: Company,
    state: str,
    state_entity_id: str,
    entity_type: str | None,
    formation_date: date | None,
    status_raw: str | None,
    status_normalized: RegistrationStatus,
    source_id: uuid.UUID | None,
) -> BusinessRegistration:
    """Create or update the per-state registration (unique by state+entity id)."""

    existing = session.scalar(
        select(BusinessRegistration).where(
            BusinessRegistration.state == state,
            BusinessRegistration.state_entity_id == state_entity_id,
        )
    )
    if existing is not None:
        existing.status_raw = status_raw
        existing.status_normalized = status_normalized
        session.flush()
        return existing

    registration = BusinessRegistration(
        company_id=company.id,
        state=state,
        state_entity_id=state_entity_id,
        entity_type=entity_type,
        formation_date=formation_date,
        status_raw=status_raw,
        status_normalized=status_normalized,
        source_id=source_id,
    )
    session.add(registration)
    session.flush()
    return registration


def add_registered_agent(
    session: Session,
    *,
    registration: BusinessRegistration,
    agent_name: str | None,
    agent_address: str | None,
    source_id: uuid.UUID | None,
) -> RegisteredAgent | None:
    """Record a registered agent (skipped when no agent data is present)."""

    if not agent_name and not agent_address:
        return None
    agent = RegisteredAgent(
        registration_id=registration.id,
        agent_name=agent_name,
        agent_address=agent_address,
        source_id=source_id,
    )
    session.add(agent)
    session.flush()
    return agent


def add_officers(
    session: Session,
    *,
    company: Company,
    officers: list[dict],
    source_id: uuid.UUID | None,
    screened: dict[str, bool] | None = None,
) -> list[CompanyOfficer]:
    """Record officers with their OFAC screening result (where screened)."""

    screened = screened or {}
    created: list[CompanyOfficer] = []
    for officer in officers:
        name = officer.get("name")
        if not name:
            continue
        record = CompanyOfficer(
            company_id=company.id,
            name=name,
            title=officer.get("title"),
            address=officer.get("address"),
            screened_ofac=screened.get(name),
            source_id=source_id,
        )
        session.add(record)
        created.append(record)
    session.flush()
    return created
