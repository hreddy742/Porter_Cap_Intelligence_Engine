"""Webhook endpoint management and delivery log (admin & ops).

Registering an endpoint returns its signing secret exactly once -- it is never
shown again, matching how Stripe/GitHub issue webhook secrets. Deliveries are
fired from the verification flow on run completion (see
``workers/verify_flow.py`` / ``services/webhooks.py``); this router only
manages subscriptions and exposes the delivery log for debugging.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_session
from porter_verify.api.schemas import (
    WebhookDeliveryOut,
    WebhookEndpointCreate,
    WebhookEndpointCreated,
    WebhookEndpointOut,
    WebhookEndpointUpdate,
)
from porter_verify.api.security import CurrentUser, require_roles
from porter_verify.db.enums import WebhookDeliveryStatus
from porter_verify.db.models import WebhookDelivery, WebhookEndpoint
from porter_verify.services.audit import record_audit
from porter_verify.services.webhooks import generate_secret

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/endpoints", response_model=WebhookEndpointCreated, status_code=201)
def create_endpoint(
    payload: WebhookEndpointCreate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("admin")),
) -> WebhookEndpoint:
    endpoint = WebhookEndpoint(
        url=payload.url,
        description=payload.description,
        secret=generate_secret(),
        created_by_email=user.email,
    )
    session.add(endpoint)
    session.flush()
    record_audit(
        session,
        actor=user.email,
        action="webhook_endpoint.created",
        entity_type="webhook_endpoint",
        entity_id=str(endpoint.id),
        after={"url": endpoint.url},
    )
    session.commit()
    session.refresh(endpoint)
    return endpoint


@router.get("/endpoints", response_model=list[WebhookEndpointOut])
def list_endpoints(
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("admin", "ops")),
) -> list[WebhookEndpoint]:
    return list(session.scalars(select(WebhookEndpoint).order_by(WebhookEndpoint.created_at)).all())


@router.patch("/endpoints/{endpoint_id}", response_model=WebhookEndpointOut)
def update_endpoint(
    endpoint_id: uuid.UUID,
    payload: WebhookEndpointUpdate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("admin")),
) -> WebhookEndpoint:
    endpoint = session.get(WebhookEndpoint, endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found.")
    before_enabled = endpoint.enabled
    endpoint.enabled = payload.enabled
    record_audit(
        session,
        actor=user.email,
        action="webhook_endpoint.enabled_updated",
        entity_type="webhook_endpoint",
        entity_id=str(endpoint.id),
        before={"enabled": before_enabled},
        after={"enabled": endpoint.enabled},
    )
    session.commit()
    session.refresh(endpoint)
    return endpoint


@router.delete("/endpoints/{endpoint_id}", status_code=204)
def delete_endpoint(
    endpoint_id: uuid.UUID,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("admin")),
) -> None:
    endpoint = session.get(WebhookEndpoint, endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found.")
    session.delete(endpoint)
    record_audit(
        session,
        actor=user.email,
        action="webhook_endpoint.deleted",
        entity_type="webhook_endpoint",
        entity_id=str(endpoint_id),
    )
    session.commit()


@router.get("/deliveries", response_model=list[WebhookDeliveryOut])
def list_deliveries(
    endpoint_id: uuid.UUID | None = Query(default=None),
    status: WebhookDeliveryStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("admin", "ops")),
) -> list[WebhookDelivery]:
    stmt = select(WebhookDelivery).order_by(WebhookDelivery.created_at.desc()).limit(limit)
    if endpoint_id is not None:
        stmt = stmt.where(WebhookDelivery.endpoint_id == endpoint_id)
    if status is not None:
        stmt = stmt.where(WebhookDelivery.status == status)
    return list(session.scalars(stmt).all())
