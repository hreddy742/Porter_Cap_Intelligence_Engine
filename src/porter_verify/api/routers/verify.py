"""Verification endpoint: start an async run and return its id to poll.

Live source lookups can be slow (seconds to minutes), so verification is async
(Cobalt's retryId pattern): POST creates a PENDING run, schedules the work in the
background, and returns the run_id immediately. The client polls GET /runs/{id}
until the run reaches a terminal state.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_evidence_store, get_registry, get_session
from porter_verify.api.limiter import limiter
from porter_verify.api.schemas import RegistryVerifyResponse, VerifyRequest, VerifyResponse
from porter_verify.api.security import CurrentUser, require_roles
from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.db.enums import RunStatus
from porter_verify.services.evidence import EvidenceStore
from porter_verify.services.screening import screen
from porter_verify.services.state_registries import (
    find_registry_match,
    registry_confidence,
    supported_states,
)
from porter_verify.workers.verify_flow import create_pending_run, run_in_background

router = APIRouter(tags=["verify"])


@router.get("/verify", response_model=RegistryVerifyResponse)
def verify_registry(
    company: str = Query(min_length=1, max_length=500),
    state: str = Query(min_length=2, max_length=2),
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops", "compliance")),
) -> RegistryVerifyResponse:
    state = state.upper()
    if state not in supported_states():
        raise HTTPException(status_code=400, detail=f"Unsupported state: {state}")

    ofac = screen(company)
    match = find_registry_match(session, company, state)
    if match is None:
        return RegistryVerifyResponse(
            verified=False,
            confidence=0.0,
            status=None,
            entity_type=None,
            formation_date=None,
            address=None,
            officers=[],
            source_url=None,
            ofac_clear=not ofac.hit,
        )

    return RegistryVerifyResponse(
        verified=True,
        confidence=registry_confidence(company, match.entity_name),
        status=match.status_raw,
        entity_type=match.entity_type,
        formation_date=match.formation_date,
        address=match.principal_address or match.mailing_address,
        officers=[item.get("name", "") for item in match.officers if isinstance(item, dict)],
        source_url=match.source_record_url,
        ofac_clear=not ofac.hit,
    )


@router.post("/verify", response_model=VerifyResponse, status_code=202)
@limiter.limit("20/minute")
def verify(
    payload: VerifyRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    session: Session = Depends(get_session),
    registry: ConnectorRegistry = Depends(get_registry),
    store: EvidenceStore = Depends(get_evidence_store),
    user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops")),
) -> VerifyResponse:
    run = create_pending_run(session, actor=user.email)

    # Run the actual flow after the response is sent; the client polls /runs/{id}.
    background_tasks.add_task(
        run_in_background,
        run_id=run.id,
        name=payload.name,
        state=payload.state,
        actor=user.email,
        session_factory=request.app.state.session_factory,
        registry=registry,
        evidence_store=store,
    )

    return VerifyResponse(
        run_id=run.id,
        run_status=RunStatus.PENDING,
        verification_status=None,
        company_id=None,
        match_confidence=None,
        message="Verification started. Poll GET /runs/{run_id} for the result.",
    )
