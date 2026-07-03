"""Targeted Nevada UCC public-search connector.

Nevada UCC filings are managed by the Secretary of State. There is no
free bulk download.

CONFIRMED BLOCKED (2026-07-02, live test): both plausible NV SOS UCC search
entry points are behind bot-management, confirmed via a real Playwright/
Chromium session:

  - https://www.nvsos.gov/sos/businesses/liens-ucc-and-federal-tax-liens/
    ucc-search returns an Akamai "Access Denied" page (reference ID format
    matches errors.edgesuite.net, Akamai's edge domain).
  - https://esos.nv.gov/EntitySearch/OnlineEntitySearch (the SilverFlume/
    entity-search backend NV UCC search is believed to route through)
    returns an Incapsula "_Incapsula_Resource" challenge iframe -- the
    same bot-management vendor confirmed blocking California's BizFile UCC
    search (see ca_ucc.py).

Bypassing either would require browser-fingerprint evasion or a paid
anti-bot bypass service -- out of scope here. search_nv_ucc() raises
NvUccBlockedError so callers can route to manual review instead of
silently returning an empty result set.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

NV_UCC_SEARCH_URL = "https://www.nvsos.gov/sos/businesses/liens-ucc-and-federal-tax-liens/ucc-search"


class NvUccBlockedError(RuntimeError):
    """Raised because NV's UCC search entry points are bot-management blocked."""


@dataclass(frozen=True)
class NevadaUccSearchResult:
    filing_number: str
    debtor_name: str
    secured_party: str | None
    filing_date: date | None
    lapse_date: date | None
    status: str


def search_nv_ucc(company_name: str) -> list[NevadaUccSearchResult]:
    """Search the NV SOS UCC portal for filings by organization debtor name.

    Always raises NvUccBlockedError -- both known NV UCC search entry
    points are bot-management blocked (Akamai on nvsos.gov, Incapsula on
    esos.nv.gov), confirmed live 2026-07-02. See module docstring.
    """
    raise NvUccBlockedError(
        f"NV UCC search for {company_name!r} is blocked: nvsos.gov returns "
        "an Akamai 'Access Denied' page and esos.nv.gov returns an "
        "Incapsula bot-management challenge. Route to manual review or "
        "contact the NV SOS UCC Division for a bulk/data-licensing "
        "arrangement."
    )


def parse_nv_ucc_results(html: str) -> list[NevadaUccSearchResult]:
    """Parse the NV UCC search results table.

    NOT YET VALIDATED against real result markup -- see NvUccBlockedError.
    """
    return []


def to_public_search_results(
    company_name: str,
    rows: list[NevadaUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert raw NV search results to the shared PublicSearchUccResult shape."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    return [
        PublicSearchUccResult(
            state="NV",
            filing_id=row.filing_number,
            debtor_name=row.debtor_name,
            filing_type="UCC1",
            status=row.status,
            search_query=query,
            source_url=NV_UCC_SEARCH_URL,
            secured_party_name=row.secured_party,
            filing_date=row.filing_date,
            termination_date=row.lapse_date if row.status == "TERMINATED" else None,
            debtor_state="NV",
            collateral_description=None,
            match_confidence=_confidence(query_normalized, row.debtor_name),
        )
        for row in rows
    ]


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    return 70
