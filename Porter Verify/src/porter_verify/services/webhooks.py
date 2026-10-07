"""Signed webhook delivery for verification run completion events.

Every enabled ``WebhookEndpoint`` receives one HMAC-SHA256 signed POST per
finished run (``event=verification.finished``), idempotent per
``(endpoint_id, verification_run_id)`` -- a run can produce at most one
delivery row per endpoint, retried in place rather than duplicated. A failed
attempt backs off and is retried by a periodic scheduler job
(``scheduler.py``) up to ``MAX_ATTEMPTS``, after which it is marked FAILED and
left for manual inspection via ``GET /webhooks/deliveries``.

The receiver verifies authenticity by recomputing
``hmac_sha256(secret, raw_body)`` and comparing it to the
``X-Porter-Signature`` header -- the same pattern Stripe/GitHub webhooks use.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.db.base import utcnow
from porter_verify.db.enums import WebhookDeliveryStatus
from porter_verify.db.models import VerificationRun, WebhookDelivery, WebhookEndpoint
from porter_verify.logging_config import get_logger

log = get_logger(__name__)

MAX_ATTEMPTS = 5
# Backoff before each successive retry, indexed by (attempt_count - 1).
_BACKOFF_MINUTES = [1, 5, 15, 60, 240]
_DELIVERY_TIMEOUT_SECONDS = 10.0
EVENT_VERIFICATION_FINISHED = "verification.finished"


def generate_secret() -> str:
    """A fresh per-endpoint signing secret, shown to the caller once at creation."""

    return f"whsec_{secrets.token_hex(24)}"


def sign_payload(secret: str, body: bytes) -> str:
    """Hex-encoded HMAC-SHA256 of the raw request body."""

    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def build_event_payload(run: VerificationRun) -> dict:
    return {
        "event": EVENT_VERIFICATION_FINISHED,
        "run_id": str(run.id),
        "run_status": run.status.value,
        "verification_status": getattr(run.verification_status, "value", None),
        "company_id": str(run.company_id) if run.company_id else None,
        "match_confidence": (
            float(run.match_confidence) if run.match_confidence is not None else None
        ),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


def enqueue_and_deliver(session: Session, run: VerificationRun) -> None:
    """Create (idempotently) and immediately attempt delivery for every enabled endpoint."""

    endpoints = session.scalars(
        select(WebhookEndpoint).where(WebhookEndpoint.enabled.is_(True))
    ).all()
    if not endpoints:
        return

    payload = build_event_payload(run)
    for endpoint in endpoints:
        delivery = session.scalar(
            select(WebhookDelivery).where(
                WebhookDelivery.endpoint_id == endpoint.id,
                WebhookDelivery.verification_run_id == run.id,
            )
        )
        if delivery is not None:
            continue  # already enqueued (and possibly already delivered) for this run
        delivery = WebhookDelivery(
            endpoint_id=endpoint.id,
            verification_run_id=run.id,
            event_type=EVENT_VERIFICATION_FINISHED,
            payload=payload,
        )
        session.add(delivery)
        session.flush()
        _attempt_delivery(delivery, endpoint)
    session.commit()


def retry_due_deliveries(session: Session) -> int:
    """Retry PENDING deliveries whose backoff window has elapsed. Returns count attempted."""

    now = utcnow()
    due = session.scalars(
        select(WebhookDelivery).where(
            WebhookDelivery.status == WebhookDeliveryStatus.PENDING,
            WebhookDelivery.next_retry_at.is_not(None),
            WebhookDelivery.next_retry_at <= now,
        )
    ).all()
    for delivery in due:
        endpoint = session.get(WebhookEndpoint, delivery.endpoint_id)
        if endpoint is None or not endpoint.enabled:
            continue
        _attempt_delivery(delivery, endpoint)
    session.commit()
    return len(due)


def _attempt_delivery(delivery: WebhookDelivery, endpoint: WebhookEndpoint) -> None:
    body = json.dumps(delivery.payload, sort_keys=True).encode("utf-8")
    signature = sign_payload(endpoint.secret, body)
    delivery.attempt_count += 1
    delivery.last_attempt_at = utcnow()
    try:
        response = httpx.post(
            endpoint.url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Porter-Signature": f"sha256={signature}",
                "X-Porter-Delivery-Id": str(delivery.id),
                "X-Porter-Event": delivery.event_type,
            },
            timeout=_DELIVERY_TIMEOUT_SECONDS,
        )
        delivery.response_code = response.status_code
        if 200 <= response.status_code < 300:
            delivery.status = WebhookDeliveryStatus.DELIVERED
            delivery.next_retry_at = None
            delivery.error = None
        else:
            _schedule_retry_or_fail(delivery, error=f"HTTP {response.status_code}")
    except httpx.HTTPError as exc:
        delivery.response_code = None
        _schedule_retry_or_fail(delivery, error=str(exc))


def _schedule_retry_or_fail(delivery: WebhookDelivery, *, error: str) -> None:
    delivery.error = error
    if delivery.attempt_count >= MAX_ATTEMPTS:
        delivery.status = WebhookDeliveryStatus.FAILED
        delivery.next_retry_at = None
        log.warning("webhook_delivery_exhausted", delivery_id=str(delivery.id), error=error)
    else:
        backoff = _BACKOFF_MINUTES[min(delivery.attempt_count - 1, len(_BACKOFF_MINUTES) - 1)]
        delivery.status = WebhookDeliveryStatus.PENDING
        delivery.next_retry_at = utcnow() + timedelta(minutes=backoff)
