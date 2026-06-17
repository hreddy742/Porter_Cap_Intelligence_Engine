"""Salesforce sync state (foundation for Phase 3 integration)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from porter_verify.db.base import Base, TimestampMixin, uuid_pk
from porter_verify.db.enums import SyncStatus


class SalesforceSyncStatus(Base, TimestampMixin):
    """Tracks the sync state between a company and a Salesforce record.

    Idempotent by ``(sf_object, sf_record_id)`` so re-running a sync updates the
    same row rather than creating duplicates. No Salesforce data is pushed until
    credentials, field mappings, and an approval flow are configured (Phase 3).
    """

    __tablename__ = "salesforce_sync_status"
    __table_args__ = (UniqueConstraint("sf_object", "sf_record_id", name="sf_object_record"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    sf_object: Mapped[str] = mapped_column(String(50), nullable=False)  # Lead | Account
    sf_record_id: Mapped[str] = mapped_column(String(50), nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, native_enum=False, length=20),
        default=SyncStatus.PENDING,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text)
