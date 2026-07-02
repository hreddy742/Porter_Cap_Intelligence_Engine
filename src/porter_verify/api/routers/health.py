"""Health and readiness endpoints (unauthenticated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from porter_verify import __version__
from porter_verify.api.deps import get_session
from porter_verify.services.state_registries import registry_counts
from porter_verify.services.ucc_intelligence import ucc_counts

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: Session = Depends(get_session)) -> dict:
    """Liveness plus registry table counts."""

    counts = registry_counts(session)
    body = {
        "status": "ok",
        "version": __version__,
        "record_counts": counts.record_counts,
        "last_refresh_timestamps": {
            state: value.isoformat() if value else None
            for state, value in counts.last_refresh_timestamps.items()
        },
    }
    body.update(ucc_counts(session))
    return body


@router.get("/ready")
def ready(session: Session = Depends(get_session)) -> dict[str, str]:
    """Readiness: the process can reach its database."""

    session.execute(text("SELECT 1"))
    return {"status": "ready"}
