"""Source health / registry endpoint (admin & ops)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_session
from porter_verify.api.schemas import (
    SourceEnabledUpdate,
    SourceHealthOut,
    SourcePolicyOut,
    SourcePolicyUpdate,
    SourceQualityOut,
)
from porter_verify.api.security import CurrentUser, require_roles
from porter_verify.services import queries
from porter_verify.services.audit import record_audit
from porter_verify.services.sources import get_source_by_name, upsert_source_policy

router = APIRouter(tags=["sources"])


@router.get("/sources/health", response_model=list[SourceHealthOut])
def source_health(
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("ops")),
) -> list[SourceHealthOut]:
    return [SourceHealthOut.model_validate(s) for s in queries.all_sources(session)]


@router.get("/sources/quality", response_model=list[SourceQualityOut])
def source_quality(
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("ops")),
) -> list[SourceQualityOut]:
    return [
        SourceQualityOut(source_name=source_name, **quality.__dict__)
        for source_name, quality in queries.latest_source_quality(session)
    ]


@router.patch("/sources/{source_name}/enabled", response_model=SourceHealthOut)
def set_source_enabled(
    source_name: str,
    payload: SourceEnabledUpdate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("admin")),
) -> SourceHealthOut:
    """Kill switch: enable/disable a source without a deploy.

    Disabling a source causes new verification runs against it to finish as
    SOURCE_UNAVAILABLE with no charge (see workers/verify_flow.py, which
    checks SourceRegistry.enabled right after resolving the source). This
    never happens automatically -- health degradation is surfaced via
    health_status, but taking a source out of rotation is always this
    deliberate, audited, human action.
    """
    source = get_source_by_name(session, source_name)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")

    before_enabled = source.enabled
    source.enabled = payload.enabled
    record_audit(
        session,
        actor=user.email,
        action="source.enabled_updated",
        entity_type="source",
        entity_id=str(source.id),
        before={"enabled": before_enabled},
        after={"enabled": source.enabled},
    )
    session.commit()
    session.refresh(source)
    return SourceHealthOut.model_validate(source)


@router.put("/sources/{source_name}/policy", response_model=SourcePolicyOut)
def update_source_policy(
    source_name: str,
    payload: SourcePolicyUpdate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("admin")),
) -> SourcePolicyOut:
    source = get_source_by_name(session, source_name)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")

    before = (
        SourcePolicyOut.model_validate(source.policy).model_dump(mode="json")
        if source.policy
        else None
    )
    policy = upsert_source_policy(session, source=source, payload=payload, actor=user.email)
    after = SourcePolicyOut.model_validate(policy).model_dump(mode="json")
    record_audit(
        session,
        actor=user.email,
        action="source.policy_updated",
        entity_type="source",
        entity_id=str(source.id),
        before=before,
        after=after,
    )
    session.commit()
    return SourcePolicyOut.model_validate(policy)
