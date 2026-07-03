"""Targeted Michigan UCC public-search connector.

Michigan UCC filings are administered by the Michigan Department of State.
No Socrata/open-data bulk dataset exists; a paid bulk subscription
($500/month under 2017 SB0520) is available but requires manual account
setup (517-335-6167 / UCCSection@Michigan.gov) with an undocumented
delivery format, so it is out of scope for an automated connector.

CONFIRMED WORKING (2026-07-03, live test) via Playwright. The free public
"Debtor name quick search" at https://ucc.michigan.gov/ucc-search is an
Angular SPA, but it works cleanly:

    1. GET the search URL. The "Organization" radio (id=personInd2) is
       already checked by default -- no click needed (attempting to click
       it can fail with "element outside viewport", a layout red herring,
       not a functional blocker).
    2. Fill #organizationName with the debtor name.
    3. Click the "Search" button.
    4. Results render as an Angular Material mat-table -- NOT a plain HTML
       <table>. Each result is a <mat-row>; each <mat-cell> inside it
       carries a `data-label` attribute identifying its column
       (e.g. data-label="Financing statement number") and its value inside
       a <p class="cell-content">. Confirmed live columns: Financing
       statement number, Lien type, Registered date, Lapse date, Status.
       The `aria-label` on the "Registered date"/"Lapse date" cells
       carries the full ISO timestamp, which this parser prefers over the
       shorter MM/DD/YYYY text in the visible <p>.

This replaces the earlier version of this connector, which never attempted
a live session and always raised MichiganUccUnavailableError with
instructions to capture the real request -- that capture is now done.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

MI_UCC_SEARCH_URL = "https://ucc.michigan.gov/ucc-search"

_ORG_NAME_SELECTOR = "#organizationName"
_SEARCH_BUTTON_SELECTOR = "button:has-text('Search')"


@dataclass(frozen=True)
class MichiganUccSearchResult:
    debtor_name: str
    filing_number: str
    lien_type: str
    filing_date: date | None
    lapse_date: date | None
    filing_status: str


def search_mi_ucc(
    company_name: str,
    *,
    include_lapsed: bool = False,
) -> list[MichiganUccSearchResult]:
    """Search Michigan UCC filings by organization name.

    Requires Playwright + the chromium browser binary.

    Args:
        company_name: Debtor / organization name to search for.
        include_lapsed: Unused -- the live UI does not expose a lapsed-filter
            control; kept for interface parity with other state connectors.
    """
    del include_lapsed
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
            page.goto(MI_UCC_SEARCH_URL, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(1500)

            org_field = page.locator(_ORG_NAME_SELECTOR)
            if org_field.count() == 0:
                raise RuntimeError(
                    f"MI UCC search field not found on {MI_UCC_SEARCH_URL}. "
                    "The portal may have been redesigned."
                )
            org_field.fill(company_name)
            page.click(_SEARCH_BUTTON_SELECTOR)
            page.wait_for_timeout(2000)

            html = page.content()
        finally:
            browser.close()

    return parse_mi_ucc_results(company_name, html)


def to_public_search_results(
    company_name: str,
    rows: list[MichiganUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert raw MI search results to the canonical PublicSearchUccResult shape."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    return [
        PublicSearchUccResult(
            state="MI",
            filing_id=row.filing_number,
            debtor_name=row.debtor_name,
            filing_type=_filing_type(row.lien_type),
            status=_status(row.filing_status, row.lapse_date),
            search_query=query,
            source_url=MI_UCC_SEARCH_URL,
            filing_date=row.filing_date,
            termination_date=row.lapse_date if _is_terminated(row.filing_status) else None,
            debtor_state="MI",
            collateral_description="Michigan public UCC status-search summary",
            match_confidence=_confidence(query_normalized, row.debtor_name),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# HTML parsing -- Angular Material mat-table with data-label attributes
# ---------------------------------------------------------------------------

_ROW_RE = re.compile(r"<mat-row\b.*?</mat-row>", re.DOTALL)
_CELL_RE = re.compile(
    r'<mat-cell\b[^>]*data-label="([^"]*)"[^>]*aria-label="([^"]*)"[^>]*>'
    r'.*?<p[^>]*>\s*([^<]*?)\s*</p>',
    re.DOTALL,
)


def parse_mi_ucc_results(company_name: str, html: str) -> list[MichiganUccSearchResult]:
    """Parse the Angular Material mat-table results into search result rows.

    Michigan's quick search returns a debtor-name summary (the search query
    itself is the debtor name shown once above the results table, not
    repeated per row), so *company_name* is used directly as debtor_name.
    """
    results: list[MichiganUccSearchResult] = []
    for row_html in _ROW_RE.findall(html):
        fields: dict[str, tuple[str, str]] = {}
        for label, aria_label, text_value in _CELL_RE.findall(row_html):
            fields[label.strip()] = (aria_label.strip(), text_value.strip())

        filing_number = fields.get("Financing statement number", ("", ""))[1]
        if not filing_number:
            continue
        lien_type = fields.get("Lien type", ("", "Initial"))[1] or "Initial"
        filing_status = fields.get("Status", ("", "Active"))[1] or "Active"

        results.append(
            MichiganUccSearchResult(
                debtor_name=company_name.strip(),
                filing_number=filing_number,
                lien_type=lien_type,
                filing_date=_parse_date_from_fields(fields.get("Registered date")),
                lapse_date=_parse_date_from_fields(fields.get("Lapse date")),
                filing_status=filing_status,
            )
        )
    return results


def _parse_date_from_fields(field: tuple[str, str] | None) -> date | None:
    if field is None:
        return None
    aria_label, text_value = field
    # Prefer the full ISO timestamp embedded in aria-label
    # (e.g. "... file date is: 2024-12-04T23:38:03.697"), fall back to the
    # shorter MM/DD/YYYY text shown in the cell.
    iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", aria_label)
    if iso_match:
        return _parse_date(iso_match.group(1))
    return _parse_date(text_value)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def _filing_type(lien_type: str) -> str:
    text = normalize_ucc_name(lien_type)
    if "TERMIN" in text or "RELEASE" in text:
        return "UCC3"
    if "AMEND" in text:
        return "AMENDMENT"
    if "CONTINU" in text:
        return "CONTINUATION"
    return "UCC1"


def _is_terminated(filing_status: str) -> bool:
    text = normalize_ucc_name(filing_status)
    return "TERMIN" in text or "LAPSED" in text or "RELEASED" in text


def _status(filing_status: str, lapse_date: date | None) -> str:
    if _is_terminated(filing_status):
        return "TERMINATED"
    if lapse_date and lapse_date < date.today():
        return "TERMINATED"
    return "ACTIVE"


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    return 70
