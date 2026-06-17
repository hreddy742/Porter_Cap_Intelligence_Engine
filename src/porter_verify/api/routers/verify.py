"""Verification endpoint: start an async run and return its id to poll.

Live source lookups can be slow (seconds to minutes), so verification is async
(Cobalt's retryId pattern): POST creates a PENDING run, schedules the work in the
background, and returns the run_id immediately. The client polls GET /runs/{id}
until the run reaches a terminal state.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_evidence_store, get_registry, get_session
from porter_verify.api.schemas import VerifyRequest, VerifyResponse
from porter_verify.api.security import CurrentUser, require_roles
from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.db.enums import RunStatus
from porter_verify.services.evidence import EvidenceStore
from porter_verify.workers.verify_flow import create_pending_run, run_in_background

router = APIRouter(tags=["verify"])


@router.post("/verify", response_model=VerifyResponse, status_code=202)
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
