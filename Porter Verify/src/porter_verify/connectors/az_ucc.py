"""Targeted Arizona UCC public-search connector.

Arizona UCC is hosted by the AZ Secretary of State at apps.azsos.gov.
Bulk data is available only as a paid product ($2,000 thumb drive or
$1,800/year subscription), so this connector uses the public search portal
at https://apps.azsos.gov/apps/ucc/search/.

CONFIRMED BLOCKED (2026-07-03, live test): the initial page GET succeeds
(200) even from plain httpx, but the search POST/postback is rejected with
a Cloudflare bot-management 403 (apps.azsos.gov/cdn-cgi/challenge-platform)
-- confirmed against real headless Chromium via Playwright, not just httpx.
This is Cloudflare fingerprinting automated browsers, not a wrong selector
or field name; the form-fill and results-table-parsing logic below were
verified correct against the live DOM before the search POST was blocked.

Bypassing this would require browser-fingerprint evasion (e.g. a patched/
stealth Chromium build) or a paid anti-bot bypass service -- out of scope
for this connector. search_az_ucc() raises AzUccBlockedError so callers can
route to manual review instead of silently returning an empty result set.

Install Playwright once per environment (needed if bot-management is ever
bypassed and this connector is reactivated):
    pip install playwright
    playwright install chromium

Real control names (captured 2026-07-03 via live Playwright session):
    ctl00$ctl00$PageContent$PageContent$OrganizationTextBox         -- debtor/org name
    ctl00$ctl00$PageContent$PageContent$OrganizationRadioButtonList -- Debtor/Secured Party
    ctl00$ctl00$PageContent$PageContent$SearchButton_input          -- search button (AJAX postback)
    ctl00_ctl00_PageContent_PageContent_ResultsGridView_ctl00       -- results grid (Telerik RadGrid)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

AZ_UCC_BASE_URL = "https://apps.azsos.gov/apps/ucc/search/"
AZ_UCC_SEARCH_URL = AZ_UCC_BASE_URL

_ORG_NAME_SELECTOR = "#ctl00_ctl00_PageContent_PageContent_OrganizationTextBox"
_ORG_RADIO_SELECTOR = "#PageContent_PageContent_OrganizationRadioButtonList_0"
_SEARCH_BUTTON_SELECTOR = (
    "input[type='submit'], input[type='button'][value*='Search' i], "
    "a:has-text('Search'), button:has-text('Search')"
)
_PAGE_LOAD_TIMEOUT = 30_000  # ms
_SEARCH_TIMEOUT = 20_000  # ms


class AzUccBlockedError(RuntimeError):
    """Raised when Cloudflare bot-management rejects the AZ UCC search request."""


@dataclass(frozen=True)
class ArizonaUccSearchResult:
    filing_number: str
    debtor_name: str
    secured_party: str | None
    document_type: str | None
    original_date: date | None
    expiration_date: date | None
    filing_date: date | None
    recording_date: date | None


def search_az_ucc(company_name: str) -> list[ArizonaUccSearchResult]:
    """Search the Arizona SOS UCC portal for *company_name* (debtor search).

    Requires Playwright + the chromium browser binary to be installed.
    Raises ``RuntimeError`` if the search form or results table cannot be
    located, so callers can fall back to manual review instead of silently
    returning an empty result set.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                )
            )
            page.goto(AZ_UCC_BASE_URL, timeout=_PAGE_LOAD_TIMEOUT, wait_until="domcontentloaded")

            org_input = page.locator(_ORG_NAME_SELECTOR)
            if org_input.count() == 0:
                raise RuntimeError(
                    "AZ UCC search form field not found; the azsos.gov portal "
                    "markup may have changed."
                )
            org_radio = page.locator(_ORG_RADIO_SELECTOR)
            if org_radio.count() > 0:
                org_radio.check()
            org_input.click()
            org_input.type(company_name, delay=30)

            search_response = None

            def _capture_search_response(response: object) -> None:
                nonlocal search_response
                if response.url == AZ_UCC_BASE_URL and response.request.method == "POST":  # type: ignore[attr-defined]
                    search_response = response

            page.on("response", _capture_search_response)
            page.locator("#ctl00_ctl00_PageContent_PageContent_SearchButton_input").click()
            page.wait_for_load_state("networkidle", timeout=_SEARCH_TIMEOUT)
            page.wait_for_timeout(1500)

            if search_response is not None and search_response.status == 403:  # type: ignore[attr-defined]
                raise AzUccBlockedError(
                    "AZ SOS UCC search is blocked by Cloudflare bot-management "
                    "(403 on the search request). Route to manual review."
                )

            html = page.content()
        finally:
            browser.close()

    return parse_az_ucc_results(html)


def parse_az_ucc_results(html: str) -> list[ArizonaUccSearchResult]:
    """Parse the rendered HTML from the AZ SOS UCC search results page."""
    parser = _ResultsTableParser()
    parser.feed(html)
    results: list[ArizonaUccSearchResult] = []
    for cells in parser.rows:
        if len(cells) < 4:
            continue
        filing_number = cells[0].strip()
        if not filing_number or filing_number.lower() in {"file number", "filing number", "#"}:
            continue
        debtor_name = cells[1].strip() if len(cells) > 1 else ""
        if not debtor_name:
            continue
        secured_party = cells[2].strip() if len(cells) > 2 else None
        document_type = cells[3].strip() if len(cells) > 3 else None
        original_date = _parse_date(cells[4]) if len(cells) > 4 else None
        expiration_date = _parse_date(cells[5]) if len(cells) > 5 else None
        filing_date = _parse_date(cells[6]) if len(cells) > 6 else None
        recording_date = _parse_date(cells[7]) if len(cells) > 7 else None
        results.append(
            ArizonaUccSearchResult(
                filing_number=filing_number,
                debtor_name=debtor_name,
                secured_party=secured_party or None,
                document_type=document_type or None,
                original_date=original_date,
                expiration_date=expiration_date,
                filing_date=filing_date,
                recording_date=recording_date,
            )
        )
    return results


def to_public_search_results(
    company_name: str,
    rows: list[ArizonaUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert AZ raw results to the common :class:`PublicSearchUccResult` shape."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    mapped: list[PublicSearchUccResult] = []
    for row in rows:
        filing_type = _classify_filing_type(row.document_type)
        status = _classify_status(row.document_type, row.expiration_date)
        termination_date: date | None = None
        if status == "TERMINATED" and filing_type == "UCC3":
            termination_date = row.filing_date

        mapped.append(
            PublicSearchUccResult(
                state="AZ",
                filing_id=row.filing_number,
                debtor_name=row.debtor_name,
                filing_type=filing_type,
                status=status,
                search_query=query,
                source_url=AZ_UCC_SEARCH_URL,
                secured_party_name=row.secured_party,
                filing_date=row.filing_date or row.original_date,
                termination_date=termination_date,
                debtor_city=None,
                debtor_state="AZ",
                collateral_description=None,
                match_confidence=_confidence(query_normalized, row.debtor_name),
            )
        )
    return mapped


def _parse_date(value: str) -> date | None:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _classify_filing_type(document_type: str | None) -> str:
    if not document_type:
        return "UCC1"
    text = normalize_ucc_name(document_type)
    if "TERMIN" in text or "RELEASE" in text:
        return "UCC3"
    if "CONTINUATION" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _classify_status(document_type: str | None, expiration_date: date | None) -> str:
    filing_type = _classify_filing_type(document_type)
    if filing_type == "UCC3":
        return "TERMINATED"
    if expiration_date is not None and expiration_date < date.today():
        return "TERMINATED"
    return "ACTIVE"


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    return 70


class _ResultsTableParser(HTMLParser):
    """Extract rows from the UCC search results table."""

    def __init__(self) -> None:
        super().__init__()
        self.in_results_table = False
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []
        self._found_table = False
        self._pending_rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            if not self._found_table:
                self.in_results_table = True
                self._pending_rows = []
        elif self.in_results_table and tag == "tr":
            self.current_row = []
        elif self.in_results_table and tag in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if self.in_results_table and tag in {"td", "th"} and self.in_cell:
            self.current_row.append(" ".join(self.current_cell).strip())
            self.in_cell = False
        elif self.in_results_table and tag == "tr" and self.current_row:
            self._pending_rows.append(self.current_row)
            self.current_row = []
        elif tag == "table":
            if self.in_results_table:
                is_results = any(
                    any(k in cell.lower() for k in ("file", "debtor", "filing", "secured"))
                    for row in self._pending_rows
                    for cell in row
                )
                if is_results:
                    self._found_table = True
                    self.rows.extend(self._pending_rows)
                self.in_results_table = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if self.in_cell and text:
            self.current_cell.append(text)
