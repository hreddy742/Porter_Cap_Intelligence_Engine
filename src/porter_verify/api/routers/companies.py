"""Company search, profile, and evidence-timeline endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_session
from porter_verify.api.schemas import (
    CompanySummary,
    EvidenceOut,
    OfficerOut,
    ProfileResponse,
    RegisteredAgentOut,
    RegistrationOut,
    RunOut,
    ScoreComponentOut,
    SearchResponse,
)
from porter_verify.api.security import CurrentUser, get_current_user, require_roles
from porter_verify.db.models import Company, VerificationRun
from porter_verify.services import queries
from porter_verify.services.audit import record_audit

router = APIRouter(tags=["companies"])

# Roles allowed to see PII-bearing data (officers, evidence detail).
_SENSITIVE_ROLES = ("underwriter", "compliance")


def _summary(company: Company, run: VerificationRun | None) -> CompanySummary:
    return CompanySummary(
        id=company.id,
        canonical_legal_name=company.canonical_legal_name,
        home_state=company.home_state,
        status_normalized=company.status_normalized,
        verification_status=run.verification_status if run else None,
        match_confidence=float(run.match_confidence)
        if run and run.match_confidence is not None
        else None,
    )


@router.get("/companies", response_model=SearchResponse)
def search(
    q: str = Query(default="", description="Name fragment to search for"),
    state: str | None = Query(default=None, max_length=2),
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(get_current_user),
) -> SearchResponse:
    rows = queries.search_companies(session, query=q, state=state)
    return SearchResponse(results=[_summary(c, r) for c, r in rows])


@router.get("/companies/{company_id}/profile", response_model=ProfileResponse)
def profile(
    company_id: uuid.UUID,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> ProfileResponse:
    company = queries.get_company(session, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found.")

    run = queries.latest_run_for(session, company_id)
    registrations = queries.registrations_for(session, company_id)
    scores = queries.scores_for_run(session, run.id) if run else []
    evidence = queries.evidence_for_company(session, company_id)

    # Officers are PII — only sensitive roles see them (field-level access).
    can_see_pii = user.role in {*_SENSITIVE_ROLES, "admin"}
    officers = queries.officers_for(session, company_id) if can_see_pii else []

    # Registered agent name is public record; the agent ADDRESS is PII-adjacent and
    # is masked for non-sensitive roles.
    agents = queries.agents_for(session, [r.id for r in registrations])
    agent_out = [
        RegisteredAgentOut(
            agent_name=a.agent_name,
            agent_address=a.agent_address if can_see_pii else None,
        )
        for a in agents
    ]

    return ProfileResponse(
        company=_summary(company, run),
        registrations=[RegistrationOut.model_validate(r) for r in registrations],
        agents=agent_out,
        officers=[OfficerOut.model_validate(o) for o in officers],
        latest_run=RunOut.model_validate(run) if run else None,
        scores=[ScoreComponentOut.model_validate(s) for s in scores],
        evidence=[EvidenceOut.model_validate(e) for e in evidence],
    )


@router.get("/companies/{company_id}/evidence", response_model=list[EvidenceOut])
def evidence_timeline(
    company_id: uuid.UUID,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles(*_SENSITIVE_ROLES)),
) -> list[EvidenceOut]:
    """Evidence timeline — a sensitive read, restricted and audited."""

    if queries.get_company(session, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found.")

    record_audit(
        session,
        actor=user.email,
        action="evidence.read",
        entity_type="company",
        entity_id=str(company_id),
    )
    session.commit()
    items = queries.evidence_for_company(session, company_id)
    return [EvidenceOut.model_validate(e) for e in items]
