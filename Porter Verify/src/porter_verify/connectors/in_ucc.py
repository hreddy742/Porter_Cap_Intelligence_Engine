"""Targeted Indiana UCC public-search connector.

Indiana UCC filings are managed by the Secretary of State's Business
Services Division at https://bsd.sos.in.gov/PublicUCCSearch, an ASP.NET
WebForms application. There is no free bulk download.

CONFIRMED BLOCKED (2026-07-02, live test): the free public debtor-name
search requires solving a CAPTCHA before returning results -- confirmed
via a real Playwright/Chromium session that filled the real search fields
and submitted the form; the response was "You must successfully complete
the Captcha." This is independent of form-field correctness (the real
fields were confirmed live: #rdDebtorName, #Organization,
#txtOrganizationName, #btnSearch). search_in_ucc() raises
InUccCaptchaRequiredError so callers can route to manual review instead of
silently returning an empty result set.

Real form flow (captured 2026-07-02 via live Playwright session):
    1. GET https://bsd.sos.in.gov/PublicUCCSearch
    2. Click #rdDebtorName (search-by radio: Filing Number / Debtor Name /
       Secured Party Name)
    3. Click #Organization (debtor-type radio: Organization / Individual)
    4. Fill #txtOrganizationName
    5. Click #btnSearch -> CAPTCHA required.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

IN_UCC_SEARCH_URL = "https://bsd.sos.in.gov/PublicUCCSearch"

_DEBTOR_RADIO_SELECTOR = "#rdDebtorName"
_ORG_RADIO_SELECTOR = "#Organization"
_ORG_NAME_SELECTOR = "#txtOrganizationName"
_SEARCH_BUTTON_SELECTOR = "#btnSearch"


class InUccCaptchaRequiredError(RuntimeError):
    """Raised when the IN UCC search portal demands a CAPTCHA solve."""


@dataclass(frozen=True)
class IndianaUccSearchResult:
    filing_number: str
    debtor_name: str
    secured_party: str | None
    filing_date: date | None
    lapse_date: date | None
    status: str


def search_in_ucc(company_name: str) -> list[IndianaUccSearchResult]:
    """Search the IN SOS UCC portal for filings by organization debtor name.

    Requires Playwright + the chromium browser binary. Raises
    ``InUccCaptchaRequiredError`` because the live portal currently demands
    a CAPTCHA solve before returning results -- confirmed 2026-07-02.
    """
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                )
            )
            page.goto(IN_UCC_SEARCH_URL, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(1000)

            page.click(_DEBTOR_RADIO_SELECTOR)
            page.wait_for_timeout(300)
            org_radio = page.locator(_ORG_RADIO_SELECTOR)
            if org_radio.count() == 0:
                raise RuntimeError(
                    "IN UCC search form field not found; the bsd.sos.in.gov "
                    "portal markup may have changed."
                )
            org_radio.click()

            org_field = page.locator(_ORG_NAME_SELECTOR)
            org_field.fill(company_name)
            page.click(_SEARCH_BUTTON_SELECTOR)
            page.wait_for_timeout(2000)

            body_text = page.inner_text("body")
            if "captcha" in body_text.lower():
                raise InUccCaptchaRequiredError(
                    "IN UCC search requires solving a CAPTCHA before returning "
                    "results. Route to manual review."
                )

            html = page.content()
        finally:
            browser.close()

    return parse_in_ucc_results(html)


def parse_in_ucc_results(html: str) -> list[IndianaUccSearchResult]:
    """Parse the IN UCC search results table.

    NOT YET VALIDATED against real result markup -- the CAPTCHA wall (see
    module docstring) prevents ever reaching a results page during
    development. Implement once CAPTCHA-gated access is resolved (e.g. a
    manual session cookie) and real result HTML can be captured.
    """
    return []


def to_public_search_results(
    company_name: str,
    rows: list[IndianaUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert raw IN search results to the shared PublicSearchUccResult shape."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    return [
        PublicSearchUccResult(
            state="IN",
            filing_id=row.filing_number,
            debtor_name=row.debtor_name,
            filing_type="UCC1",
            status=row.status,
            search_query=query,
            source_url=IN_UCC_SEARCH_URL,
            secured_party_name=row.secured_party,
            filing_date=row.filing_date,
            termination_date=row.lapse_date if row.status == "TERMINATED" else None,
            debtor_state="IN",
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
