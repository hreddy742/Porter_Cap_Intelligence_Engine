"""Source governance and quality measurement services."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.api.schemas import SourcePolicyUpdate
from porter_verify.db.models import SourcePolicy, SourceRegistry


def get_source_by_name(session: Session, name: str) -> SourceRegistry | None:
    return session.scalar(select(SourceRegistry).where(SourceRegistry.name == name))


def upsert_source_policy(
    session: Session,
    *,
    source: SourceRegistry,
    payload: SourcePolicyUpdate,
    actor: str,
) -> SourcePolicy:
    """Create or replace a source's governance policy without touching credentials."""

    policy = source.policy
    if policy is None:
        policy = SourcePolicy(source_id=source.id)
        session.add(policy)

    for field, value in payload.model_dump().items():
        setattr(policy, field, value)

    if payload.legal_review_status == "approved":
        policy.approved_by = actor
        policy.approved_at = datetime.now(UTC)
    else:
        policy.approved_by = None
        policy.approved_at = None

    session.flush()
    return policy
