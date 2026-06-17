"""Manual review decision endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_session
from porter_verify.api.schemas import ReviewRequest, ReviewResponse
from porter_verify.api.security import CurrentUser, require_roles
from porter_verify.services.review import RunNotFoundError, record_decision

router = APIRouter(tags=["review"])


@router.post("/review/{run_id}/decision", response_model=ReviewResponse)
def decide(
    run_id: uuid.UUID,
    payload: ReviewRequest,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("underwriter")),
) -> ReviewResponse:
    try:
        record = record_decision(
            session,
            run_id=run_id,
            reviewer_email=user.email,
            decision=payload.decision,
            reason=payload.reason,
            candidate_chosen=payload.candidate_chosen,
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Verification run not found.") from exc
    session.commit()
    return ReviewResponse(id=record.id, run_id=run_id, decision=record.decision)
