"""Source registry and credential references.

The registry drives connector selection (by capability + state coverage + health).
Credentials hold only secret *references* — never plaintext keys.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from porter_verify.db.base import Base, TimestampMixin, uuid_pk


class SourceRegistry(Base, TimestampMixin):
    """A data source / connector and its declared capabilities and coverage."""

    __tablename__ = "source_registry"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # e.g. ["entity","status","officers","ofac"]
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    # Two-letter state codes covered, or [] for nationwide/non-state sources.
    states: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    cost_per_lookup: Mapped[float] = mapped_column(Numeric(8, 3), default=0, nullable=False)
    health_status: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    credentials: Mapped[list[SourceCredential]] = relationship(back_populates="source")
    policy: Mapped[SourcePolicy | None] = relationship(
        back_populates="source", cascade="all, delete-orphan", uselist=False
    )
    quality_daily: Mapped[list[SourceQualityDaily]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class SourceCredential(Base, TimestampMixin):
    """A reference to a secret stored in a secrets manager. No plaintext here."""

    __tablename__ = "source_credentials"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_registry.id"), nullable=False)
    # Pointer into the secrets manager, e.g. "vault://porter/sos_vendor/api_key".
    secret_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    env: Mapped[str] = mapped_column(String(20), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped[SourceRegistry] = relationship(back_populates="credentials")


class SourcePolicy(Base, TimestampMixin):
    """Governance rules that must be known before a source reaches production."""

    __tablename__ = "source_policies"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_registry.id"), unique=True, nullable=False
    )
    acquisition_method: Mapped[str] = mapped_column(String(30), default="unknown", nullable=False)
    legal_review_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    allowed_purposes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    retention_days: Mapped[int | None] = mapped_column(Integer)
    freshness_sla_hours: Mapped[int | None] = mapped_column(Integer)
    terms_url: Mapped[str | None] = mapped_column(String(1000))
    owner: Mapped[str | None] = mapped_column(String(320))
    approved_by: Mapped[str | None] = mapped_column(String(320))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped[SourceRegistry] = relationship(back_populates="policy")


class SourceQualityDaily(Base, TimestampMixin):
    """Daily source reliability, freshness, and cost measurements."""

    __tablename__ = "source_quality_daily"
    __table_args__ = (UniqueConstraint("source_id", "metric_date", name="source_quality_day"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_registry.id"), nullable=False)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_latency_ms: Mapped[int | None] = mapped_column(Integer)
    freshness_pass_rate: Mapped[float | None] = mapped_column(Numeric(5, 4))
    estimated_cost: Mapped[float] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    schema_drift_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    source: Mapped[SourceRegistry] = relationship(back_populates="quality_daily")
