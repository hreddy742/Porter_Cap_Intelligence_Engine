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
    UccLeadOut,
    UccLeadUpdate,
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
from porter_verify.db.base import utcnow
from porter_verify.db.enums import RegistrationStatus, UccSearchStatus
from porter_verify.db.models import (
    Company,
    UccExitSignal,
    UccFiling,
    UccLead,
    UccRefreshLog,
    UccSearchOrder,
)
from porter_verify.services.audit import record_audit
from porter_verify.services.companies import upsert_company
from porter_verify.services.normalization import dedupe_key, normalize_name
from porter_verify.services.ucc_intelligence import (
    add_known_factor,
    find_ucc_filings,
    known_factors,
    normalize_ucc_name,
)
from porter_verify.services.ucc_public_search import SUPPORTED_STATES, ingest_public_search_results, run_targeted_search

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
            "Indiana has no free bulk UCC dataset. Confirmed live "
            "(2026-07-02) that the free public debtor-name search requires "
            "solving a CAPTCHA before returning results. Connector raises "
            "InUccCaptchaRequiredError rather than silently returning zero "
            "results."
        ),
    },
    "NV": {
        "status": "blocked",
        "source_url": "https://www.nvsos.gov/sos/businesses/liens-ucc-and-federal-tax-liens/ucc-search",
        "notes": (
            "Nevada has no free bulk UCC dataset. Confirmed live "
            "(2026-07-02) that both plausible UCC search entry points are "
            "bot-management blocked: nvsos.gov returns an Akamai 'Access "
            "Denied' page, and esos.nv.gov returns an Incapsula bot-"
            "management challenge (same vendor confirmed blocking CA). "
            "Connector raises NvUccBlockedError."
        ),
    },
    "AR": {
        "status": "targeted_public_search",
        "source_url": "https://bcs.sos.arkansas.gov/search/ucc",
        "notes": (
            "Arkansas has no free bulk UCC dataset. Confirmed live "
            "(2026-07-02): targeted search via Playwright works with no "
            "bot-management block, returning real filing data."
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
    "NY": {
        "status": "targeted_public_search",
        "source_url": "https://ucc-efiling.dos.ny.gov/OnlineUCCSearch/OnlineUCCSearch",
        "notes": (
            "New York has no free bulk UCC dataset. Confirmed live "
            "(2026-07-03): targeted search via Playwright works (fixed the "
            "real radio/field selectors), returning 383 matches for a test "
            "query; only the first page (10 results) is currently read."
        ),
    },
    "CA": {
        "status": "blocked",
        "source_url": "https://bizfileonline.sos.ca.gov/search/ucc",
        "notes": (
            "California has no free bulk UCC dataset (bulk downloads require a "
            "paid SOS account). Confirmed live (2026-07-03) that the search "
            "portal is behind Incapsula bot-management -- Playwright gets "
            "redirected to an _Incapsula_Resource challenge frame instead of "
            "the real app. Connector raises CaUccBlockedError rather than "
            "silently returning zero results."
        ),
    },
    "IL": {
        "status": "blocked",
        "source_url": "https://apps.ilsos.gov/uccsearch/",
        "notes": (
            "Illinois has no free bulk UCC dataset (bulk access costs $2,500 "
            "one-time + $200/week). Confirmed live (2026-07-03) that the "
            "search portal is bot-managed: repeated attempts produced a 403 "
            "WAF block page, a connection timeout, and a 200 that never "
            "actually executed the search -- inconsistent, but genuinely "
            "blocked. Connector raises IlUccBlockedError on a detected block."
        ),
    },
    "PA": {
        "status": "blocked",
        "source_url": "https://file.dos.pa.gov/search/ucc",
        "notes": (
            "Pennsylvania has no free bulk UCC dataset; certified searches "
            "require a paper UCC11 form. Confirmed live (2026-07-03) that "
            "the search portal is behind Cloudflare bot-management (403 "
            "challenge page with a Ray ID), the same class of block "
            "confirmed for AZ and NC. Connector raises PaUccBlockedError."
        ),
    },
    "MI": {
        "status": "targeted_public_search",
        "source_url": "https://ucc.michigan.gov/ucc-search",
        "notes": (
            "Michigan's public search is an Angular SPA. Confirmed live "
            "(2026-07-03): no bot-management block encountered; Playwright "
            "automation of the Angular Material results table works "
            "correctly, returning real filing data."
        ),
    },
    "NC": {
        "status": "blocked",
        "source_url": "https://www.sosnc.gov/online_services/search/by_title/_uniform_commercial_code",
        "notes": (
            "North Carolina has no free bulk UCC dataset (paid FTP "
            "subscription only, $4,000-$5,200/yr). Confirmed live "
            "(2026-07-03) that sosnc.gov is behind Cloudflare bot-management "
            "-- even a real headless Chromium session gets a 403 with a "
            "Cloudflare challenge redirect. Connector raises NcUccBlockedError "
            "rather than silently returning zero results."
        ),
    },
    "MD": {
        "status": "blocked",
        "source_url": "https://egov.maryland.gov/SDAT/UCCFiling/UCCMainPage.aspx",
        "notes": (
            "Maryland has no free bulk UCC dataset. Confirmed live (real "
            "Playwright session, correct search field) that the free public "
            "Name Search requires solving a CAPTCHA before returning results "
            "-- connector raises MdUccCaptchaRequiredError rather than "
            "silently returning zero results."
        ),
    },
    "MN": {
        "status": "targeted_public_search",
        "source_url": "https://mblsportal.sos.mn.gov/Secured/SearchUCC",
        "notes": (
            "Minnesota supports free file-number lookups. Debtor-name search "
            "requires a paid MBLS account (MN_UCC_USERNAME/MN_UCC_PASSWORD); "
            "raises MnUccAuthRequired/MnUccPaywallError without credentials."
        ),
    },
    "SC": {
        "status": "targeted_public_search",
        "source_url": "https://ucconline.sc.gov/UCCFiling/MainMenu.aspx",
        "notes": (
            "South Carolina has no free bulk UCC dataset ($12,000/yr paid "
            "subscriber feed). Confirmed live (2026-07-03): the free public "
            "Name Search works with no CAPTCHA via a two-step flow (name "
            "match selection, then filing retrieval) automated with "
            "Playwright."
        ),
    },
    "KY": {
        "status": "targeted_public_search",
        "source_url": "https://web.sos.ky.gov/ftucc/search.aspx",
        "notes": (
            "Kentucky's only bulk feed is a paid ($1,500/mo) OIDC-gated Bulk "
            "Data Service. Confirmed live (2026-07-03): targeted public "
            "search works via plain HTTP (no bot-detection/CAPTCHA), "
            "combining standard + fuzzy-match result tables."
        ),
    },
    "MO": {
        "status": "blocked",
        "source_url": "https://bsd.sos.mo.gov/LoginWelcome.aspx?lobID=0",
        "notes": (
            "Missouri gates all UCC search access behind a Corporate "
            "E-account (ACH pre-note setup, ~7 business days); no free "
            "unauthenticated search path exists. Connector raises "
            "MissouriUccAuthRequiredError until account access is secured."
        ),
    },
    "AZ": {
        "status": "blocked",
        "source_url": "https://apps.azsos.gov/apps/ucc/search/",
        "notes": (
            "Arizona bulk UCC data is a paid product ($2,000 one-time or "
            "$1,800/yr). The public search portal is protected by Cloudflare "
            "bot-management: confirmed live that the search POST returns 403 "
            "even from a real headless Chromium session, after the initial "
            "page load succeeds. Connector raises AzUccBlockedError rather "
            "than silently returning zero results."
        ),
    },
    "WI": {
        "status": "targeted_public_search",
        "source_url": "https://wims.dfi.wi.gov/uccsearch",
        "notes": (
            "Wisconsin DFI sells weekly bulk files ($250/file or $500/mo); "
            "no free bulk dataset exists. Confirmed live (2026-07-03): "
            "targeted search via Playwright automation of the WIMS Angular "
            "SPA works (fixed the Individual/Organization mat-select "
            "interaction)."
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
    if state not in SUPPORTED_STATES:
        lookup = _lookup_response(session, company, state)
        supported_list = ", ".join(sorted(SUPPORTED_STATES))
        return UccPublicSearchResponse(
            state=state,
            company=company,
            supported=False,
            imported_count=0,
            message=(
                "Live targeted public search is currently supported for "
                f"{supported_list}, not {state}."
            ),
            lookup=lookup,
        )

    try:
        results = run_targeted_search(state, company)
    except RuntimeError as exc:
        # Every connector-level "search is blocked/gated" exception (e.g.
        # AzUccBlockedError, MdUccCaptchaRequiredError, MissouriUccAuthRequiredError)
        # is a RuntimeError. Surface it as a clean, typed response instead
        # of letting it crash the request with an unhandled 500.
        lookup = _lookup_response(session, company, state)
        return UccPublicSearchResponse(
            state=state,
            company=company,
            supported=True,
            imported_count=0,
            message=f"{state} live search could not complete: {exc}",
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


@router.post("/ucc/exits/{signal_id}/promote", response_model=UccLeadOut, status_code=201)
def promote_exit_signal(
    signal_id: str,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops", "compliance")),
) -> UccLead:
    """Promote a UCC-3 exit signal into an actionable, trackable lead.

    Idempotent: promoting an already-promoted signal returns the existing
    lead rather than raising or creating a duplicate.
    """
    signal = session.get(UccExitSignal, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Exit signal not found.")

    existing = session.scalar(
        select(UccLead).where(UccLead.exit_signal_id == signal_id)
    )
    if existing is not None:
        return existing

    company = session.scalar(
        select(Company).where(
            Company.dedupe_key == dedupe_key(signal.state, normalize_name(signal.debtor_name))
        )
    )
    lead = UccLead(
        id=uuid.uuid4(),
        exit_signal_id=signal_id,
        company_id=company.id if company else None,
        debtor_name=signal.debtor_name,
        state=signal.state,
        created_by_email=user.email,
    )
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead


@router.get("/ucc/leads", response_model=list[UccLeadOut])
def list_leads(
    status: str | None = Query(default=None),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops", "compliance")),
) -> list[UccLead]:
    filters = []
    if status:
        filters.append(UccLead.status == status)
    if state:
        filters.append(UccLead.state == state.upper())
    return list(
        session.scalars(
            select(UccLead)
            .where(*filters)
            .order_by(UccLead.created_at.desc())
            .limit(limit)
        )
    )


@router.patch("/ucc/leads/{lead_id}", response_model=UccLeadOut)
def update_lead(
    lead_id: uuid.UUID,
    request: UccLeadUpdate,
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops", "compliance")),
) -> UccLead:
    lead = session.get(UccLead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")

    if request.status is not None:
        lead.status = request.status
    if request.assigned_to_email is not None:
        lead.assigned_to_email = request.assigned_to_email
    if request.notes is not None:
        lead.notes = request.notes

    session.commit()
    session.refresh(lead)
    return lead


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
