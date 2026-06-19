"""Underwriting endpoints for manual, source-backed UCC search coverage."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_session
from porter_verify.api.schemas import UccSearchComplete, UccSearchCreate, UccSearchOut
from porter_verify.api.security import CurrentUser, require_roles
from porter_verify.db.base import utcnow
from porter_verify.db.enums import UccSearchStatus
from porter_verify.db.models import Company, UccSearchOrder
from porter_verify.services.audit import record_audit

router = APIRouter(tags=["ucc"])


@router.post(
    "/companies/{company_id}/ucc-searches",
    response_model=UccSearchOut,
    status_code=status.HTTP_201_CREATED,
)
def create_search(
    company_id: uuid.UUID,
    request: UccSearchCreate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("underwriter")),
) -> UccSearchOrder:
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found.")

    pending_id = session.scalar(
        select(UccSearchOrder.id).where(
            UccSearchOrder.company_id == company.id,
            UccSearchOrder.state == request.state,
            UccSearchOrder.status == UccSearchStatus.PENDING,
        )
    )
    if pending_id is not None:
        raise HTTPException(
            status_code=409,
            detail="A pending UCC search already exists for this company and state.",
        )

    order = UccSearchOrder(
        company_id=company.id,
        state=request.state,
        search_name=company.canonical_legal_name,
        requested_by_email=user.email,
    )
    session.add(order)
    session.flush()
    record_audit(
        session,
        actor=user.email,
        action="ucc_search.created",
        entity_type="ucc_search_order",
        entity_id=str(order.id),
        after={"company_id": str(company.id), "state": order.state, "status": order.status.value},
    )
    session.commit()
    session.refresh(order)
    return order


@router.post("/ucc-searches/{search_id}/complete", response_model=UccSearchOut)
def complete_search(
    search_id: uuid.UUID,
    request: UccSearchComplete,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("underwriter")),
) -> UccSearchOrder:
    order = session.get(UccSearchOrder, search_id)
    if order is None:
        raise HTTPException(status_code=404, detail="UCC search order not found.")
    if order.status is UccSearchStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Completed UCC searches are immutable.")

    order.status = UccSearchStatus.COMPLETED
    order.outcome = request.outcome
    order.source_url = request.source_url
    order.notes = request.notes
    order.completed_by_email = user.email
    order.completed_at = utcnow()
    record_audit(
        session,
        actor=user.email,
        action="ucc_search.completed",
        entity_type="ucc_search_order",
        entity_id=str(order.id),
        before={"status": UccSearchStatus.PENDING.value},
        after={"status": order.status.value, "outcome": order.outcome.value},
    )
    session.commit()
    session.refresh(order)
    return order
