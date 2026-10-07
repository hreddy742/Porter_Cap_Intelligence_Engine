"""Tests for the audit service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.db.models import AuditLog
from porter_verify.services.audit import record_audit


def test_record_audit_appends_entry(db_session: Session) -> None:
    record_audit(
        db_session,
        actor="dana@portercap.net",
        action="run.completed",
        entity_type="verification_run",
        entity_id="abc-123",
        before={"status": "needs_review"},
        after={"status": "verified"},
        request_id="req-1",
    )
    db_session.commit()

    entry = db_session.scalars(select(AuditLog)).one()
    assert entry.actor == "dana@portercap.net"
    assert entry.action == "run.completed"
    assert entry.before == {"status": "needs_review"}
    assert entry.after == {"status": "verified"}
    assert entry.occurred_at is not None


def test_audit_entries_are_ordered_by_id(db_session: Session) -> None:
    record_audit(db_session, actor="system", action="first")
    record_audit(db_session, actor="system", action="second")
    db_session.commit()

    actions = list(db_session.scalars(select(AuditLog.action).order_by(AuditLog.id)))
    assert actions == ["first", "second"]
