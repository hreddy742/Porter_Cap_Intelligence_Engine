"""Company search, profile, and evidence-timeline endpoints."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_session
from porter_verify.api.schemas import (
    CompanySummary,
    EvidenceOut,
    OfficerOut,
    ProfileResponse,
    RecentBusinessFilters,
    RecentBusinessOut,
    RecentBusinessPagination,
    RecentBusinessResponse,
    RegisteredAgentOut,
    RegistrationOut,
    RunOut,
    ScoreComponentOut,
    SearchResponse,
    UccSearchOut,
)
from porter_verify.api.security import CurrentUser, get_current_user, require_roles
from porter_verify.db.models import Company, VerificationRun
from porter_verify.services import queries
from porter_verify.services.audit import record_audit
from porter_verify.services.recent_businesses import (
    MODELS,
    RecentBusinessRecord,
    find_recent_businesses,
    get_recent_business,
)

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


def _recent_out(item: RecentBusinessRecord) -> RecentBusinessOut:
    return RecentBusinessOut(
        state=item.state,
        entity_id=item.entity.entity_id,
        legal_name=item.entity.entity_name,
        entity_type=item.entity.entity_type,
        registration_or_formation_date=item.entity.formation_date,
        date_basis=item.date_basis,
        status_raw=item.entity.status_raw,
        jurisdiction=item.jurisdiction,
        principal_address=item.entity.principal_address,
        source_record_url=item.source_record_url,
        domestic_signal=item.domestic_signal,
        active_signal=item.active_signal,
        nonprofit_signal=item.nonprofit_signal,
        relevant_entity_signal=item.relevant_entity_signal,
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


@router.get("/recent-businesses", response_model=RecentBusinessResponse)
def recent_businesses(
    states: str = Query(default="CO,CT,OR,OH"),
    formed_from: date | None = Query(default=None),
    formed_to: date | None = Query(default=None),
    q: str = Query(default="", max_length=200),
    sort_by: Literal["formation_date", "legal_name", "entity_id", "state"] = Query(
        default="formation_date"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(get_current_user),
) -> RecentBusinessResponse:
    """Recent registration feed with conservative, source-specific lead filters."""

    selected_states = list(dict.fromkeys(s.strip().upper() for s in states.split(",") if s.strip()))
    unsupported = sorted(set(selected_states) - set(MODELS))
    if not selected_states or unsupported:
        detail = "Choose at least one supported state."
        if unsupported:
            detail = f"Unsupported states: {', '.join(unsupported)}."
        raise HTTPException(status_code=422, detail=detail)

    end = formed_to or date.today()
    start = formed_from or end - timedelta(days=30)
    if start > end:
        raise HTTPException(status_code=422, detail="formed_from must be on or before formed_to.")
    normalized_query = q.strip()
    result_page = find_recent_businesses(
        session,
        states=selected_states,
        formed_from=start,
        formed_to=end,
        query=normalized_query,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return RecentBusinessResponse(
        results=[_recent_out(item) for item in result_page.records],
        filters=RecentBusinessFilters(
            states=selected_states,
            formed_from=start,
            formed_to=end,
            q=normalized_query,
            sort_by=sort_by,
            sort_order=sort_order,
        ),
        pagination=RecentBusinessPagination(
            page=page,
            page_size=page_size,
            total=result_page.total,
            total_pages=(result_page.total + page_size - 1) // page_size,
        ),
    )


@router.get("/recent-businesses/{state}/{entity_id}", response_model=RecentBusinessOut)
def recent_business_detail(
    state: str,
    entity_id: str,
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(get_current_user),
) -> RecentBusinessOut:
    normalized_state = state.upper()
    if normalized_state not in MODELS:
        raise HTTPException(status_code=404, detail="Supported state not found.")
    item = get_recent_business(session, state=normalized_state, entity_id=entity_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Business record not found.")
    return _recent_out(item)


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
    ucc_searches = queries.ucc_searches_for(session, company_id) if can_see_pii else []

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
        ucc_searches=[UccSearchOut.model_validate(item) for item in ucc_searches],
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
