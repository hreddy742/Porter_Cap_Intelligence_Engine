"""Source health / registry endpoint (admin & ops)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_session
from porter_verify.api.schemas import SourceHealthOut
from porter_verify.api.security import CurrentUser, require_roles
from porter_verify.services import queries

router = APIRouter(tags=["sources"])


@router.get("/sources/health", response_model=list[SourceHealthOut])
def source_health(
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("ops")),
) -> list[SourceHealthOut]:
    return [SourceHealthOut.model_validate(s) for s in queries.all_sources(session)]
