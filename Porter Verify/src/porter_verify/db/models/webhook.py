"""Signed webhook subscriptions and their per-event delivery log.

An endpoint's ``secret`` is generated server-side and shown to the caller once
(at creation); every delivery is HMAC-SHA256 signed with it so the receiver can
verify authenticity (see ``services/webhooks.py``). Delivery is idempotent per
``(endpoint_id, verification_run_id)`` -- one run produces at most one delivery
row per endpoint, retried in place rather than duplicated.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from porter_verify.db.base import Base, TimestampMixin, uuid_pk
from porter_verify.db.enums import WebhookDeliveryStatus


class WebhookEndpoint(Base, TimestampMixin):
    """A customer-configured URL that receives signed verification events."""

    __tablename__ = "webhook_endpoints"

    id: Mapped[uuid.UUID] = uuid_pk()
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    secret: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    created_by_email: Mapped[str] = mapped_column(String(320), nullable=False)

    # Deliveries are this endpoint's operational log, not an audit record --
    # deleting the endpoint (not just disabling it) takes its delivery history
    # with it rather than leaving orphaned rows or failing on the FK.
    deliveries: Mapped[list[WebhookDelivery]] = relationship(
        back_populates="endpoint", cascade="all, delete-orphan"
    )


class WebhookDelivery(Base, TimestampMixin):
    """One delivery attempt record for one (endpoint, verification run) pair."""

    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "endpoint_id", "verification_run_id", name="uq_webhook_deliveries_endpoint_run"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("webhook_endpoints.id"), nullable=False
    )
    verification_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verification_runs.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        Enum(WebhookDeliveryStatus, native_enum=False, length=20),
        default=WebhookDeliveryStatus.PENDING,
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_code: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)

    endpoint: Mapped[WebhookEndpoint] = relationship(back_populates="deliveries")
