"""Verification run detail endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_session
from porter_verify.api.schemas import EvidenceOut, RunDetailResponse, RunOut, ScoreComponentOut
from porter_verify.api.security import CurrentUser, get_current_user
from porter_verify.services import queries

router = APIRouter(tags=["runs"])


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run(
    run_id: uuid.UUID,
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(get_current_user),
) -> RunDetailResponse:
    run = queries.get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Verification run not found.")

    return RunDetailResponse(
        run=RunOut.model_validate(run),
        scores=[
            ScoreComponentOut.model_validate(s) for s in queries.scores_for_run(session, run_id)
        ],
        evidence=[EvidenceOut.model_validate(e) for e in queries.evidence_for_run(session, run_id)],
    )
