"""Targeted Wisconsin UCC public-search connector.

Wisconsin UCC filings are managed by the DFI (Department of Financial
Institutions) at https://wims.dfi.wi.gov/uccsearch. The search interface
is an Angular Material single-page application -- plain HTTP POST scraping
will not work because the page requires JS execution to render the search
form and return results.

CONFIRMED WORKING (2026-07-03, live test) via Playwright. Real form
structure (differs from an earlier version of this connector, which
guessed radio/toggle selectors that don't exist on this page):

- The "Individual" / "Organization" toggle is a `mat-select` dropdown
  (Angular Material), not a radio group or button-toggle. Click the
  `mat-select` element, then click the "Organization" `mat-option`.
- Selecting "Organization" reveals a single text input with
  placeholder="Organization's Name" (its id is dynamically generated,
  e.g. mat-input-9 -- select by placeholder, not id).
- Submit via the visible "Search" button (`role=button, name=Search`).
- Results render in a plain HTML table with 7 columns, in this exact
  order (confirmed live against 20 real American Express filings):
      IFS #, Filing Type, Debtor Name, Secured Party Name,
      Debtor City & State, Filed Date/Time, Status
  There is no separate lapse-date column -- Status is a literal
  "Active"/"Terminated"-style string already computed by the portal.
  City and state arrive as one combined field ("EAU CLAIRE, Wisconsin").
- Results paginate (10 per page); this connector reads the first page
  only. A follow-up enhancement could click through additional pages.

This connector uses Playwright (``playwright`` Python package):
    pip install playwright
    playwright install chromium

Bulk data is available from DFI for a paid subscription ($250/file or
$500/month). Contact DFI-UCC@dfi.wisconsin.gov or (608) 266-8915 for
purchase details. A bulk connector can be added once the subscription
and file format are confirmed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

WI_UCC_SEARCH_URL = "https://wims.dfi.wi.gov/uccsearch"
WI_UCC_SOURCE_URL = "https://dfi.wi.gov/Pages/BusinessServices/UCC/SearchLienFilings.aspx"

_ORG_NAME_INPUT_SELECTOR = "input[placeholder=\"Organization's Name\"]"


@dataclass(frozen=True)
class WisconsinUccSearchResult:
    """Parsed row from the WIMS UCC search results table."""

    filing_number: str
    filing_type: str
    debtor_name: str
    secured_party: str | None
    debtor_city: str | None
    debtor_state: str | None
    filing_date: date | None
    status: str


def search_wi_ucc(
    company_name: str,
    *,
    headless: bool = True,
    timeout_ms: int = 30_000,
) -> list[WisconsinUccSearchResult]:
    """Search the Wisconsin DFI WIMS UCC portal for *company_name*.

    Requires Playwright + the chromium browser binary.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "The 'playwright' package is required for the Wisconsin UCC connector. "
            "Install it with: pip install playwright && playwright install chromium"
        ) from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        try:
            page = browser.new_page()
            page.set_default_timeout(timeout_ms)

            page.goto(WI_UCC_SEARCH_URL, wait_until="networkidle")

            # Switch the Individual/Organization mat-select to "Organization".
            page.locator("mat-select").first.click()
            page.get_by_role("option", name="Organization").click()

            org_input = page.locator(_ORG_NAME_INPUT_SELECTOR)
            if org_input.count() == 0:
                raise RuntimeError(
                    "WI UCC: could not locate the Organization's Name input after "
                    "switching the search-type dropdown. The wims.dfi.wi.gov "
                    "portal structure may have changed."
                )
            org_input.fill(company_name)

            page.get_by_role("button", name="Search").click()
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
            page.wait_for_timeout(1000)

            html = page.content()
        finally:
            browser.close()

    return parse_wi_ucc_results(html)


def to_public_search_results(
    company_name: str,
    rows: list[WisconsinUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert raw search results to the canonical ``PublicSearchUccResult`` list."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    results = []
    for row in rows:
        results.append(
            PublicSearchUccResult(
                state="WI",
                filing_id=row.filing_number,
                debtor_name=row.debtor_name,
                filing_type=_normalize_filing_type(row.filing_type),
                status=_normalize_status(row.status),
                search_query=query,
                source_url=WI_UCC_SEARCH_URL,
                filing_date=row.filing_date,
                debtor_city=row.debtor_city,
                debtor_state=row.debtor_state or "WI",
                secured_party_name=row.secured_party,
                collateral_description=None,
                match_confidence=_confidence(query_normalized, row.debtor_name),
            )
        )
    return results


def parse_wi_ucc_results(html: str) -> list[WisconsinUccSearchResult]:
    """Parse WIMS results page HTML into a list of search result records.

    Live-confirmed column order (7 columns): IFS #, Filing Type, Debtor
    Name, Secured Party Name, Debtor City & State, Filed Date/Time, Status.
    """
    from html.parser import HTMLParser  # noqa: PLC0415

    class _TableParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self._in_table = False
            self._in_cell = False
            self._current_cell: list[str] = []
            self._current_row: list[str] = []
            self.rows: list[list[str]] = []

        def handle_starttag(
            self, tag: str, attrs: list[tuple[str, str | None]]
        ) -> None:
            if tag == "table":
                self._in_table = True
            elif self._in_table and tag == "tr":
                self._current_row = []
            elif self._in_table and tag in {"td", "th"}:
                self._in_cell = True
                self._current_cell = []

        def handle_endtag(self, tag: str) -> None:
            if self._in_table and tag in {"td", "th"} and self._in_cell:
                self._current_row.append(" ".join(self._current_cell).strip())
                self._in_cell = False
            elif self._in_table and tag == "tr" and self._current_row:
                self.rows.append(self._current_row)
                self._current_row = []
            elif self._in_table and tag == "table":
                self._in_table = False

        def handle_data(self, data: str) -> None:
            if self._in_cell:
                text = data.strip()
                if text:
                    self._current_cell.append(text)

    parser = _TableParser()
    parser.feed(html)

    results: list[WisconsinUccSearchResult] = []
    for cells in parser.rows:
        if len(cells) < 7:
            continue
        filing_number = cells[0].strip()
        if not filing_number or filing_number.lower() in {"ifs #", "ifs#", "ifs"}:
            continue
        filing_type = cells[1].strip()
        debtor_name = cells[2].strip()
        if not debtor_name:
            continue
        secured_party = cells[3].strip() or None
        city, state_name = _parse_city_state(cells[4])
        filing_date = _parse_datetime(cells[5])
        status_raw = cells[6].strip()

        results.append(
            WisconsinUccSearchResult(
                filing_number=filing_number,
                filing_type=filing_type,
                debtor_name=debtor_name,
                secured_party=secured_party,
                debtor_city=city,
                debtor_state=state_name,
                filing_date=filing_date,
                status=status_raw,
            )
        )
    return results


def _parse_city_state(raw: str) -> tuple[str | None, str | None]:
    """Split a "CITY, State Name" field into (city, state)."""
    if not raw or "," not in raw:
        return (raw.strip() or None, None)
    city, _, state_name = raw.partition(",")
    return city.strip() or None, state_name.strip() or None


def _parse_datetime(value: str) -> date | None:
    if not value:
        return None
    text = value.strip().split(" ")[0]
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_filing_type(raw: str) -> str:
    text = raw.upper()
    if "TERMIN" in text or "RELEASE" in text:
        return "UCC3"
    if "CONTINUATION" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _normalize_status(status_raw: str) -> str:
    text = status_raw.upper().strip()
    if "ACTIVE" in text:
        return "ACTIVE"
    if any(word in text for word in ("TERMINAT", "RELEASE", "LAPSED")):
        return "TERMINATED"
    return "ACTIVE"


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if not query_normalized:
        return 70
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized in debtor_normalized:
        return 90
    return 70
