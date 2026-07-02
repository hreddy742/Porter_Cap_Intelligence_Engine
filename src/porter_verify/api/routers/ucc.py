"""Underwriting endpoints for manual, source-backed UCC search coverage."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from porter_verify.api.deps import get_session
from porter_verify.api.schemas import (
    KnownFactorCreate,
    KnownFactorOut,
    UccActiveFilingOut,
    UccCoverageOut,
    UccCoverageResponse,
    UccExitSignalOut,
    UccLookupResponse,
    UccManualSearchCreate,
    UccPublicSearchCreate,
    UccPublicSearchResponse,
    UccSearchComplete,
    UccSearchCreate,
    UccSearchOut,
    UccTerminatedFilingOut,
)
from porter_verify.api.security import CurrentUser, require_roles
from porter_verify.connectors.idaho_ucc import (
    search_idaho_ucc,
)
from porter_verify.connectors.idaho_ucc import (
    to_public_search_results as idaho_public_search_results,
)
from porter_verify.connectors.new_jersey_ucc import (
    search_new_jersey_ucc,
)
from porter_verify.connectors.new_jersey_ucc import (
    to_public_search_results as new_jersey_public_search_results,
)
from porter_verify.db.base import utcnow
from porter_verify.db.enums import RegistrationStatus, UccSearchStatus
from porter_verify.db.models import Company, UccExitSignal, UccFiling, UccRefreshLog, UccSearchOrder
from porter_verify.services.audit import record_audit
from porter_verify.services.companies import upsert_company
from porter_verify.services.ucc_intelligence import (
    add_known_factor,
    find_ucc_filings,
    known_factors,
    normalize_ucc_name,
)
from porter_verify.services.ucc_public_search import ingest_public_search_results

router = APIRouter(tags=["ucc"])

_UCC_COVERAGE = {
    "CO": {
        "status": "bulk_loaded",
        "source_url": "https://www.sos.state.co.us/pubs/business/uccHome.html",
        "notes": "Colorado UCC data is loaded from public bulk/state source files.",
    },
    "CT": {
        "status": "bulk_loaded",
        "source_url": "https://service.ct.gov/business/s/onlinebusinesssearch",
        "notes": "Connecticut UCC data is loaded from public bulk/state source files.",
    },
    "FL": {
        "status": "bulk_loaded",
        "source_url": "https://dos.fl.gov/sunbiz/search/download/",
        "notes": "Florida UCC data is loaded from Sunbiz public bulk files.",
    },
    "ID": {
        "status": "targeted_public_search",
        "source_url": "https://sosbiz.idaho.gov/search/ucc",
        "notes": "Idaho supports targeted live public search; bulk extract is not free.",
    },
    "IN": {
        "status": "blocked",
        "source_url": "https://bsd.sos.in.gov/PublicUCCSearch",
        "notes": (
            "Indiana public search currently blocks automated access with "
            "IP/CAPTCHA controls."
        ),
    },
    "IA": {
        "status": "blocked",
        "source_url": "https://filings.sos.iowa.gov/UCCSearch/UCC",
        "notes": (
            "Iowa has a public UCC search UI, but direct connector calls require "
            "a browser reCAPTCHA token."
        ),
    },
    "MI": {
        "status": "blocked",
        "source_url": "https://ucc.michigan.gov/ucc-search",
        "notes": (
            "Michigan has a public UCC search UI, but the underlying API returned "
            "401 without an authorized browser session."
        ),
    },
    "NJ": {
        "status": "targeted_public_search",
        "source_url": "https://www.njportal.com/DOR/UCC/Search",
        "notes": (
            "New Jersey supports targeted live public search with "
            "summary-level public fields."
        ),
    },
    "OR": {
        "status": "bulk_loaded",
        "source_url": "https://data.oregon.gov/",
        "notes": "Oregon UCC data is loaded from public open-data extracts.",
    },
    "TN": {
        "status": "blocked",
        "source_url": "https://tncab.tnsos.gov/ucc-debtor-search",
        "notes": (
            "Tennessee has a public UCC debtor search UI, but live automated "
            "search is gated by Cloudflare Turnstile."
        ),
    },
    "WV": {
        "status": "blocked",
        "source_url": "https://apps.wv.gov/SOS/UCC/Search",
        "notes": (
            "West Virginia has a public UCC search UI, but the public search API "
            "requires reCAPTCHA verification before adding a debtor term."
        ),
    },
}


@router.get("/ucc", response_model=UccLookupResponse)
def lookup_ucc(
    company: str = Query(min_length=1, max_length=500),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops", "compliance")),
) -> UccLookupResponse:
    state = state.upper() if state else None
    return _lookup_response(session, company, state)


@router.post("/ucc/public-search", response_model=UccPublicSearchResponse)
def public_search_ucc(
    request: UccPublicSearchCreate,
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops", "compliance")),
) -> UccPublicSearchResponse:
    state = request.state.upper()
    company = request.company.strip()
    if state == "NJ":
        source_rows = search_new_jersey_ucc(company)
        results = new_jersey_public_search_results(company, source_rows)
    elif state == "ID":
        source_rows = search_idaho_ucc(company)
        results = idaho_public_search_results(company, source_rows)
    else:
        lookup = _lookup_response(session, company, state)
        return UccPublicSearchResponse(
            state=state,
            company=company,
            supported=False,
            imported_count=0,
            message=(
                "Live targeted public search is currently supported for "
                f"ID and NJ, not {state}."
            ),
            lookup=lookup,
        )

    imported_count = ingest_public_search_results(session, results)
    lookup = _lookup_response(session, company, state)
    return UccPublicSearchResponse(
        state=state,
        company=company,
        supported=True,
        imported_count=imported_count,
        message=f"Imported {imported_count} {state} public-search UCC result(s).",
        lookup=lookup,
    )


@router.get("/ucc/coverage", response_model=UccCoverageResponse)
def ucc_coverage(
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops", "compliance")),
) -> UccCoverageResponse:
    counts = dict(
        session.execute(
            select(UccFiling.state, func.count()).group_by(UccFiling.state)
        ).all()
    )
    refreshes = dict(
        session.execute(
            select(UccRefreshLog.state, func.max(UccRefreshLog.finished_at)).group_by(
                UccRefreshLog.state
            )
        ).all()
    )
    states = [
        UccCoverageOut(
            state=state,
            status=meta["status"],
            record_count=counts.get(state, 0),
            last_refresh=refreshes.get(state),
            source_url=meta["source_url"],
            notes=meta["notes"],
        )
        for state, meta in sorted(_UCC_COVERAGE.items())
    ]
    return UccCoverageResponse(states=states)


@router.post("/ucc/manual-searches", response_model=UccSearchOut, status_code=201)
def create_manual_search(
    request: UccManualSearchCreate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("underwriter", "ops", "admin")),
) -> UccSearchOrder:
    company = upsert_company(
        session,
        legal_name=request.company.strip(),
        home_state=request.state,
        status=RegistrationStatus.UNKNOWN,
    )
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
            detail="A pending manual UCC search already exists for this company and state.",
        )

    order = UccSearchOrder(
        company_id=company.id,
        state=request.state,
        search_name=company.canonical_legal_name,
        requested_by_email=user.email,
        notes=request.notes,
    )
    session.add(order)
    session.flush()
    record_audit(
        session,
        actor=user.email,
        action="ucc_search.manual_created",
        entity_type="ucc_search_order",
        entity_id=str(order.id),
        after={
            "company_id": str(company.id),
            "state": order.state,
            "status": order.status.value,
        },
    )
    session.commit()
    session.refresh(order)
    return order


@router.get("/ucc/manual-searches", response_model=list[UccSearchOut])
def list_manual_searches(
    status_filter: UccSearchStatus | None = Query(default=UccSearchStatus.PENDING, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("underwriter", "ops", "admin")),
) -> list[UccSearchOrder]:
    filters = []
    if status_filter is not None:
        filters.append(UccSearchOrder.status == status_filter)
    return list(
        session.scalars(
            select(UccSearchOrder)
            .where(*filters)
            .order_by(UccSearchOrder.created_at.asc())
            .limit(limit)
        )
    )


@router.get("/ucc/exits", response_model=list[UccExitSignalOut])
def list_exit_signals(
    state: str | None = Query(default=None, min_length=2, max_length=2),
    min_strength: str | None = Query(default=None, pattern="^(HOT|WARM)$"),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops", "compliance")),
) -> list[UccExitSignal]:
    filters = []
    if state:
        filters.append(UccExitSignal.state == state.upper())
    if min_strength == "HOT":
        filters.append(UccExitSignal.signal_strength == "HOT")
    elif min_strength == "WARM":
        filters.append(UccExitSignal.signal_strength.in_(("HOT", "WARM")))
    return list(
        session.scalars(
            select(UccExitSignal)
            .where(*filters)
            .order_by(UccExitSignal.days_since_exit.asc())
            .limit(limit)
        )
    )


@router.get("/ucc/known-factors", response_model=list[KnownFactorOut])
def list_known_factors(
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops", "compliance")),
):
    return known_factors(session)


@router.post("/ucc/known-factors", response_model=KnownFactorOut, status_code=201)
def create_known_factor(
    request: KnownFactorCreate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("ops", "compliance", "admin")),
):
    return add_known_factor(
        session,
        company_name=request.company_name,
        lender_type=request.lender_type,
        notes=request.notes,
        added_by=user.email,
    )


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


def _freshest_exit_signal(
    session: Session, company: str, state: str | None
) -> UccExitSignal | None:
    filters = [UccExitSignal.debtor_normalized == normalize_ucc_name(company)]
    if state:
        filters.append(UccExitSignal.state == state)
    return session.scalar(
        select(UccExitSignal)
        .where(*filters)
        .order_by(UccExitSignal.days_since_exit.asc())
        .limit(1)
    )


def _lookup_response(session: Session, company: str, state: str | None) -> UccLookupResponse:
    filings = find_ucc_filings(session, company, state)
    active = [
        UccActiveFilingOut(
            secured_party=filing.secured_party_name,
            filing_date=filing.filing_date,
            collateral=filing.collateral_description,
            lender_type=filing.lender_type,
            is_factoring=filing.is_factoring_related,
            is_mca=filing.is_mca_related,
            status=filing.status,
            acquisition_method=filing.acquisition_method,
            match_confidence=filing.match_confidence,
        )
        for filing in filings
        if filing.status == "ACTIVE"
    ]
    terminated = [
        UccTerminatedFilingOut(
            secured_party=filing.secured_party_name,
            filing_date=filing.filing_date,
            termination_date=filing.termination_date,
            lender_type=filing.lender_type,
            days_since_exit=_days_since(filing.termination_date),
            acquisition_method=filing.acquisition_method,
            match_confidence=filing.match_confidence,
        )
        for filing in filings
        if filing.status == "TERMINATED" or filing.termination_date is not None
    ]
    exit_signal = _freshest_exit_signal(session, company, state)
    return UccLookupResponse(
        has_active_ucc=bool(active),
        active_filings=active,
        terminated_filings=terminated,
        ucc_exit_signal=exit_signal is not None,
        days_since_exit=exit_signal.days_since_exit if exit_signal else None,
        previous_factor=exit_signal.previous_factor if exit_signal else None,
        signal_strength=exit_signal.signal_strength if exit_signal else "NONE",
    )


def _days_since(value: date | None) -> int | None:
    if value is None:
        return None
    return (date.today() - value).days
