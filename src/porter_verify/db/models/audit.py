"""Audit logs, operational error logs, and generated reports."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from porter_verify.db.base import Base, CapturedAtMixin, utcnow, uuid_pk


class AuditLog(Base):
    """Append-only audit trail for mutations and sensitive reads.

    Written for every important action (runs, decisions, evidence reads, admin
    changes). Uses a monotonic bigint id so entries have a natural order.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(320), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[str | None] = mapped_column(String(100))
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    request_id: Mapped[str | None] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ErrorLog(Base):
    """Operational errors (connector failures, etc.) for the error dashboard."""

    __tablename__ = "error_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_registry.id"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("verification_runs.id"))
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class GeneratedReport(Base, CapturedAtMixin):
    """A generated KYB packet PDF, stored with its hash for integrity."""

    __tablename__ = "generated_reports"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1000), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
