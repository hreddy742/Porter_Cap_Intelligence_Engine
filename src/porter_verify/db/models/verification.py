"""Verification runs and their append-only evidence.

APPEND-ONLY / WORM: ``verification_runs``, ``raw_source_events``, and
``evidence_items`` are never updated or deleted once written. In production the DB
role lacks UPDATE/DELETE on these; in the MVP the service layer never mutates them
and tests assert immutability. ``verification_runs`` is the one exception that is
updated only to record its own terminal state (status/finished_at) during the run.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from porter_verify.db.base import Base, CapturedAtMixin, utcnow, uuid_pk
from porter_verify.db.enums import EvidenceType, RunStatus, VerificationStatus


class VerificationRun(Base):
    """One execution of the verification flow for a company."""

    __tablename__ = "verification_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("companies.id"))
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    trigger: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    match_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    risk_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False, length=30),
        default=RunStatus.PENDING,
        nullable=False,
    )
    # The derived overall verification outcome (VERIFIED / NEEDS_REVIEW / ...).
    # Distinct from ``status`` above, which is the run's lifecycle state.
    verification_status: Mapped[VerificationStatus | None] = mapped_column(
        Enum(VerificationStatus, native_enum=False, length=30)
    )
    # Version of the scoring + normalization logic used, for reproducibility.
    score_version: Mapped[str | None] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    raw_events: Mapped[list[RawSourceEvent]] = relationship(back_populates="run")
    evidence: Mapped[list[EvidenceItem]] = relationship(back_populates="run")
    scores: Mapped[list[ConfidenceScore]] = relationship(back_populates="run")


class RawSourceEvent(Base):
    """A verbatim source response, stored BEFORE any parsing (enables reprocessing)."""

    __tablename__ = "raw_source_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    verification_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verification_runs.id"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_registry.id"), nullable=False)
    request: Mapped[dict | None] = mapped_column(JSON)
    response_blob: Mapped[dict | None] = mapped_column(JSON)
    response_code: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    # SHA-256 of the canonicalized raw response (tamper-evidence).
    raw_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cost_credits: Mapped[float] = mapped_column(Numeric(8, 3), default=0, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    run: Mapped[VerificationRun] = relationship(back_populates="raw_events")


class EvidenceItem(Base, CapturedAtMixin):
    """Immutable proof artifact (WORM). New runs add evidence; nothing is overwritten."""

    __tablename__ = "evidence_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    verification_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verification_runs.id"), nullable=False
    )
    type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType, native_enum=False, length=20), nullable=False
    )
    # Pointer to the artifact in the evidence object store (or local dir in dev).
    storage_uri: Mapped[str] = mapped_column(String(1000), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # Optional human-facing source reference (e.g. the SOS record URL).
    source_url: Mapped[str | None] = mapped_column(String(1000))

    run: Mapped[VerificationRun] = relationship(back_populates="evidence")


class ConfidenceScore(Base, CapturedAtMixin):
    """One explainable component of a run's confidence (value + weight + reason)."""

    __tablename__ = "confidence_scores"

    id: Mapped[uuid.UUID] = uuid_pk()
    verification_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verification_runs.id"), nullable=False
    )
    component: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)

    run: Mapped[VerificationRun] = relationship(back_populates="scores")
