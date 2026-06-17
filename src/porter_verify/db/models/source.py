"""Source registry and credential references.

The registry drives connector selection (by capability + state coverage + health).
Credentials hold only secret *references* — never plaintext keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String
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
