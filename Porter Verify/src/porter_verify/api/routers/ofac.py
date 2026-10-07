"""OFAC screening endpoint for internal lead gating."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from porter_verify.api.limiter import limiter
from porter_verify.api.schemas import OfacMatchOut, OfacResponse
from porter_verify.api.security import CurrentUser, require_roles
from porter_verify.services.normalization import normalize_name
from porter_verify.services.ofac import get_ofac_metadata_by_name
from porter_verify.services.screening import screen

router = APIRouter(tags=["ofac"])


@router.get("/ofac", response_model=OfacResponse)
@limiter.limit("60/minute")
def check_ofac(
    request: Request,
    company: str = Query(min_length=1, max_length=500),
    _user: CurrentUser = Depends(require_roles("sales", "underwriter", "ops", "compliance")),
) -> OfacResponse:
    result = screen(company)
    if not result.hit:
        return OfacResponse(company=company, clear=True, match=None)

    best = result.matches[0]
    query_key = normalize_name(company)
    match_key = normalize_name(best.sanctioned_name)
    program, is_alias = get_ofac_metadata_by_name().get(match_key, (None, False))
    return OfacResponse(
        company=company,
        clear=False,
        match=OfacMatchOut(
            match_name=best.sanctioned_name,
            match_type="alias" if is_alias else "exact" if query_key == match_key else "partial",
            score=best.score,
            program=program,
        ),
    )
