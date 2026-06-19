"""UCC search coverage records attached to the canonical company spine."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from porter_verify.db.base import Base, TimestampMixin, uuid_pk
from porter_verify.db.enums import UccSearchOutcome, UccSearchStatus


class UccSearchOrder(Base, TimestampMixin):
    """An exact-name, state-level UCC search and its source-backed outcome."""

    __tablename__ = "ucc_search_orders"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id"), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    search_name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[UccSearchStatus] = mapped_column(
        Enum(UccSearchStatus, native_enum=False, length=20),
        default=UccSearchStatus.PENDING,
        nullable=False,
    )
    outcome: Mapped[UccSearchOutcome | None] = mapped_column(
        Enum(UccSearchOutcome, native_enum=False, length=30)
    )
    source_url: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str | None] = mapped_column(Text)
    requested_by_email: Mapped[str] = mapped_column(String(320), nullable=False)
    completed_by_email: Mapped[str | None] = mapped_column(String(320))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
