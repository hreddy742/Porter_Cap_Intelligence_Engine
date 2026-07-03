"""Verification endpoint: start an async run and return its id to poll.

Live source lookups can be slow (seconds to minutes), so verification is async
(Cobalt's retryId pattern): POST creates a PENDING run, schedules the work in the
background, and returns the run_id immediately. The client polls GET /runs/{id}
until the run reaches a terminal state.
"""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_evidence_store, get_registry, get_session
from porter_verify.api.limiter import limiter
from porter_verify.api.schemas import RegistryVerifyResponse, VerifyRequest, VerifyResponse
from porter_verify.api.security import CurrentUser, require_roles
from porter_verify.config import get_settings
from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.db.base import utcnow
from porter_verify.db.enums import RunStatus
from porter_verify.services.evidence import EvidenceStore
from porter_verify.services.screening import screen
from porter_verify.services.state_registries import (
    find_registry_match,
    registry_confidence,
    supported_states,
)
from porter_verify.workers.verify_flow import (
    create_pending_run,
    find_cached_run,
    find_run_by_idempotency_key,
    run_in_background,
)

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
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> VerifyResponse:
    # A client retrying the same request (e.g. after a dropped response) with the
    # same Idempotency-Key gets the original run back instead of a second run and a
    # second source charge.
    if idempotency_key:
        existing = find_run_by_idempotency_key(session, idempotency_key)
        if existing is not None:
            return _to_response(
                existing,
                message="Idempotency-Key already used; returning the original run. No new charge.",
            )

    # Even without a key, an identical (name, state) query answered recently is
    # served from that result rather than re-querying the live source.
    cached = find_cached_run(
        session,
        name=payload.name,
        state=payload.state,
        ttl_minutes=get_settings().verify_cache_ttl_minutes,
    )
    if cached is not None:
        finished_at = cached.finished_at
        if finished_at.tzinfo is None:
            # SQLite drops tzinfo even for DateTime(timezone=True) columns; the
            # value was always written in UTC (see db/base.utcnow), so treat a
            # naive read as UTC rather than crashing on aware-vs-naive subtraction.
            finished_at = finished_at.replace(tzinfo=UTC)
        age_seconds = int((utcnow() - finished_at).total_seconds())
        return _to_response(
            cached,
            message=f"Served from a cached result ({age_seconds}s old). No new source charge.",
            cached=True,
            cache_age_seconds=age_seconds,
        )

    run = create_pending_run(
        session,
        name=payload.name,
        state=payload.state,
        idempotency_key=idempotency_key,
        actor=user.email,
    )

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


def _to_response(
    run,
    *,
    message: str,
    cached: bool = False,
    cache_age_seconds: int | None = None,
) -> VerifyResponse:
    return VerifyResponse(
        run_id=run.id,
        run_status=run.status,
        verification_status=run.verification_status,
        company_id=run.company_id,
        match_confidence=float(run.match_confidence) if run.match_confidence is not None else None,
        message=message,
        cached=cached,
        cache_age_seconds=cache_age_seconds,
    )
