"""Health and readiness endpoints (unauthenticated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from porter_verify import __version__
from porter_verify.api.deps import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up."""

    return {"status": "ok", "version": __version__}


@router.get("/ready")
def ready(session: Session = Depends(get_session)) -> dict[str, str]:
    """Readiness: the process can reach its database."""

    session.execute(text("SELECT 1"))
    return {"status": "ready"}
