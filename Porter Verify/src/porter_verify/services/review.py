"""Review service: record immutable human decisions on verification runs.

A reviewer's decision is a historical fact: we never mutate a prior decision, we
append a new one. Each decision captures a before/after snapshot and is audited.
The decision is the human override referenced by downstream workflows (plan §7.10).
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from porter_verify.db.enums import ReviewDecision
from porter_verify.db.models import ReviewDecisionRecord, VerificationRun
from porter_verify.services.audit import record_audit


class RunNotFoundError(LookupError):
    """Raised when a review targets a verification run that does not exist."""


def record_decision(
    session: Session,
    *,
    run_id: uuid.UUID,
    reviewer_email: str,
    decision: ReviewDecision,
    reason: str | None = None,
    candidate_chosen: str | None = None,
) -> ReviewDecisionRecord:
    """Append a review decision for a run and audit it (caller commits)."""

    run = session.get(VerificationRun, run_id)
    if run is None:
        raise RunNotFoundError(str(run_id))

    before = {"verification_status": getattr(run.verification_status, "value", None)}
    record = ReviewDecisionRecord(
        verification_run_id=run_id,
        decision=decision,
        reason=reason,
        candidate_chosen=candidate_chosen,
        before=before,
        after={"decision": decision.value},
    )
    session.add(record)
    record_audit(
        session,
        actor=reviewer_email,
        action="review.decided",
        entity_type="verification_run",
        entity_id=str(run_id),
        before=before,
        after={"decision": decision.value, "reason": reason},
    )
    session.flush()
    return record
