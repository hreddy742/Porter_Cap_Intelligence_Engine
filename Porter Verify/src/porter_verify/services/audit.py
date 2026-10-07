"""Audit service: append-only record of important actions and sensitive reads.

Every mutation (verification runs, review decisions, admin changes) and every
sensitive read (evidence, officers) should call ``record_audit``. The audit trail
is append-only — entries are never updated or deleted.

Security: never put secrets or full PII in ``before``/``after``; store identifiers
and status changes, not credentials or raw personal data.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porter_verify.db.models import AuditLog


def record_audit(
    session: Session,
    *,
    actor: str,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Append an audit entry to the session (caller commits).

    ``actor`` is the acting user's identity (email/sso_sub) or ``"system"`` for
    automated actions. ``action`` is a short verb phrase, e.g. ``"run.completed"``.
    """

    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        request_id=request_id,
    )
    session.add(entry)
    return entry
