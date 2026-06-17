"""Verification endpoint: run the end-to-end flow for a business."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_evidence_store, get_registry, get_session
from porter_verify.api.schemas import VerifyRequest, VerifyResponse
from porter_verify.api.security import CurrentUser, require_roles
from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.services.evidence import EvidenceStore
from porter_verify.workers.verify_flow import run_verification

router = APIRouter(tags=["verify"])


@router.post("/verify", response_model=VerifyResponse)
def verify(
    payload: VerifyRequest,
    session: Session = Depends(get_session),
    registry: ConnectorRegistry = Depends(get_registry),
    store: EvidenceStore = Depends(get_evidence_store),
    user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops")),
) -> VerifyResponse:
    outcome = run_verification(
        session,
        registry=registry,
        evidence_store=store,
        name=payload.name,
        state=payload.state,
        actor=user.email,
    )
    return VerifyResponse(
        run_id=outcome.run_id,
        run_status=outcome.run_status,
        verification_status=outcome.verification_status,
        company_id=outcome.company_id,
        match_confidence=outcome.match_confidence,
        message=outcome.message,
    )
