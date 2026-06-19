"""Read queries for the API and dashboard.

These are read-only helpers that assemble the data each screen needs. They live in
the service layer (not the routers) so they stay testable and reusable.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.db.models import (
    BusinessRegistration,
    Company,
    CompanyOfficer,
    ConfidenceScore,
    EvidenceItem,
    RegisteredAgent,
    SourceQualityDaily,
    SourceRegistry,
    VerificationRun,
)
from porter_verify.services.normalization import normalize_name


def latest_run_for(session: Session, company_id: uuid.UUID) -> VerificationRun | None:
    """The most recent verification run for a company, if any."""

    return session.scalar(
        select(VerificationRun)
        .where(VerificationRun.company_id == company_id)
        .order_by(VerificationRun.started_at.desc())
        .limit(1)
    )


def search_companies(
    session: Session, *, query: str, state: str | None = None, limit: int = 25
) -> list[tuple[Company, VerificationRun | None]]:
    """Find companies whose normalized name contains the query (optionally by state)."""

    needle = normalize_name(query)
    # A query the user typed but that normalizes to "" (e.g. "...") is unsearchable
    # -> match nothing (NOT everything via contains("")). A truly blank query falls
    # through to a browse (no name filter).
    if query.strip() and not needle:
        return []

    stmt = select(Company)
    if needle:
        stmt = stmt.where(Company.normalized_name.contains(needle))
    if state:
        stmt = stmt.where(Company.home_state == state.upper())
    stmt = stmt.order_by(Company.canonical_legal_name).limit(limit)

    companies = list(session.scalars(stmt))
    return [(c, latest_run_for(session, c.id)) for c in companies]


def get_company(session: Session, company_id: uuid.UUID) -> Company | None:
    return session.get(Company, company_id)


def registrations_for(session: Session, company_id: uuid.UUID) -> list[BusinessRegistration]:
    return list(
        session.scalars(
            select(BusinessRegistration).where(BusinessRegistration.company_id == company_id)
        )
    )


def agents_for(session: Session, registration_ids: list[uuid.UUID]) -> list[RegisteredAgent]:
    if not registration_ids:
        return []
    return list(
        session.scalars(
            select(RegisteredAgent).where(RegisteredAgent.registration_id.in_(registration_ids))
        )
    )


def officers_for(session: Session, company_id: uuid.UUID) -> list[CompanyOfficer]:
    return list(
        session.scalars(select(CompanyOfficer).where(CompanyOfficer.company_id == company_id))
    )


def get_run(session: Session, run_id: uuid.UUID) -> VerificationRun | None:
    return session.get(VerificationRun, run_id)


def scores_for_run(session: Session, run_id: uuid.UUID) -> list[ConfidenceScore]:
    return list(
        session.scalars(
            select(ConfidenceScore).where(ConfidenceScore.verification_run_id == run_id)
        )
    )


def evidence_for_run(session: Session, run_id: uuid.UUID) -> list[EvidenceItem]:
    return list(
        session.scalars(
            select(EvidenceItem)
            .where(EvidenceItem.verification_run_id == run_id)
            .order_by(EvidenceItem.captured_at)
        )
    )


def evidence_for_company(session: Session, company_id: uuid.UUID) -> list[EvidenceItem]:
    """All evidence across all of a company's runs, newest first (timeline)."""

    return list(
        session.scalars(
            select(EvidenceItem)
            .join(VerificationRun, EvidenceItem.verification_run_id == VerificationRun.id)
            .where(VerificationRun.company_id == company_id)
            .order_by(EvidenceItem.captured_at.desc())
        )
    )


def all_sources(session: Session) -> list[SourceRegistry]:
    return list(session.scalars(select(SourceRegistry).order_by(SourceRegistry.name)))


def latest_source_quality(session: Session) -> list[tuple[str, SourceQualityDaily]]:
    """Return the newest quality measurement available for each source."""

    rows = session.execute(
        select(SourceRegistry.name, SourceQualityDaily)
        .join(SourceQualityDaily, SourceQualityDaily.source_id == SourceRegistry.id)
        .order_by(SourceRegistry.name, SourceQualityDaily.metric_date.desc())
    )
    latest: dict[str, SourceQualityDaily] = {}
    for source_name, quality in rows:
        latest.setdefault(source_name, quality)
    return list(latest.items())
