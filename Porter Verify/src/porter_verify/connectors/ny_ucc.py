"""Targeted New York UCC public-search connector.

NY has no free bulk download. The DOS UCC Image Retrieval System costs $300/month
and only provides TIFF images of recent filings — not useful for structured data.

CONFIRMED WORKING (2026-07-03, live test) via Playwright. Real form flow
(differs from an earlier version of this connector, which guessed generic
selectors like "label:has-text('Organization')" that don't exist on this
page):

    1. GET the search URL. Default mode is "Filing Number" search.
    2. Click #rdbDebtor to switch to "Debtor Name" search mode.
    3. Click #rdbOrg to select the Organization sub-type (vs Individual).
    4. Fill #UCCSearch_UCCSerach_txtOrgName (site's own typo, "UCCSerach",
       is real -- not a mistake to "fix").
    5. Click #UCCSearch_UCCSearch_btnSearch.
    6. Results render in table#xhtml_grid, paginated 10/page. Live-confirmed
       column order (9 columns, no secured-party or collateral columns
       exist in this list view, contrary to an earlier version of this
       connector which assumed 11 columns including those):
           Lien Number, Serial Number, Lien Subtype, Debtor Name,
           Debtor Address, Debtor Type, Filing Date/Time, Lapse Date/Time,
           Lien Status
    This connector reads only the first page (10 results); a follow-up
    enhancement could page through '#xhtml_grid + a:has-text("Next")'.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

NY_UCC_SEARCH_URL = (
    "https://ucc-efiling.dos.ny.gov/OnlineUCCSearch/OnlineUCCSearch"
)

# Delay between successive searches to avoid hammering the portal.
_REQUEST_DELAY_SECONDS = 2.0

_DEBTOR_RADIO_SELECTOR = "#rdbDebtor"
_ORG_RADIO_SELECTOR = "#rdbOrg"
_ORG_NAME_SELECTOR = "#UCCSearch_UCCSerach_txtOrgName"
_SEARCH_BUTTON_SELECTOR = "#UCCSearch_UCCSearch_btnSearch"
_RESULTS_TABLE_SELECTOR = "#xhtml_grid"


@dataclass(frozen=True)
class NewYorkUccSearchResult:
    filing_number: str
    serial_number: str | None
    lien_subtype: str | None
    debtor_name: str | None
    debtor_address: str | None
    debtor_type: str | None
    filing_date: date | None
    lapse_date: date | None
    lien_status: str | None


# ---------------------------------------------------------------------------
# Primary public interface
# ---------------------------------------------------------------------------

def search_ny_ucc(
    company_name: str,
    *,
    delay: float = _REQUEST_DELAY_SECONDS,
) -> list[NewYorkUccSearchResult]:
    """Search the NY DOS UCC portal for filings by organization debtor name.

    Args:
        company_name: Debtor organization name to search.
        delay: Seconds to sleep after the search completes (rate limiting).

    Returns:
        List of :class:`NewYorkUccSearchResult` dataclasses (first page only).

    Raises:
        ImportError: If ``playwright`` is not installed.
        RuntimeError: If the page cannot be loaded or the form cannot be found.
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "playwright is required for NY UCC searches. "
            "Install it with: pip install playwright && playwright install chromium"
        ) from exc

    html = _fetch_results_html(company_name)
    if delay:
        time.sleep(delay)
    return parse_ny_ucc_results(html)


def to_public_search_results(
    company_name: str,
    rows: list[NewYorkUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert raw NY search rows to the shared :class:`PublicSearchUccResult` type."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    results: list[PublicSearchUccResult] = []
    for row in rows:
        debtor = row.debtor_name or ""
        city, state_abbr, zip_code = _split_address(row.debtor_address)
        status = _canonical_status(row.lien_status)
        results.append(
            PublicSearchUccResult(
                state="NY",
                filing_id=row.filing_number,
                debtor_name=debtor,
                filing_type=_canonical_filing_type(row.lien_subtype),
                status=status,
                search_query=query,
                source_url=NY_UCC_SEARCH_URL,
                secured_party_name=None,
                filing_date=row.filing_date,
                termination_date=row.lapse_date if status == "TERMINATED" else None,
                collateral_description=None,
                debtor_address=row.debtor_address,
                debtor_city=city,
                debtor_state=state_abbr,
                debtor_zip=zip_code,
                match_confidence=_confidence(query_normalized, debtor),
            )
        )
    return results


# ---------------------------------------------------------------------------
# HTML parsing (for pages already fetched via Playwright)
# ---------------------------------------------------------------------------

def parse_ny_ucc_results(html: str) -> list[NewYorkUccSearchResult]:
    """Parse the HTML of the NY UCC search results page.

    Live-confirmed columns (2026-07-03): Lien Number, Serial Number, Lien
    Subtype, Debtor Name, Debtor Address, Debtor Type, Filing Date/Time,
    Lapse Date/Time, Lien Status (9 columns, table#xhtml_grid).
    """
    parser = _ResultsTableParser()
    parser.feed(html)
    rows: list[NewYorkUccSearchResult] = []
    for cells in parser.rows:
        if len(cells) < 9:
            continue
        first = cells[0].strip().lower()
        if first in {"lien number", "filing number", "filing #", "#"}:
            continue
        filing_number = cells[0].strip()
        if not filing_number:
            continue
        rows.append(
            NewYorkUccSearchResult(
                filing_number=filing_number,
                serial_number=_cell(cells, 1),
                lien_subtype=_cell(cells, 2),
                debtor_name=_cell(cells, 3),
                debtor_address=_cell(cells, 4),
                debtor_type=_cell(cells, 5),
                filing_date=_parse_date(_cell(cells, 6)),
                lapse_date=_parse_date(_cell(cells, 7)),
                lien_status=_cell(cells, 8),
            )
        )
    return rows


# ---------------------------------------------------------------------------
# Playwright automation
# ---------------------------------------------------------------------------

def _fetch_results_html(company_name: str) -> str:
    """Drive the NY UCC SPA with Playwright and return the results page HTML."""
    from playwright.sync_api import sync_playwright  # type: ignore[import]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page.goto(NY_UCC_SEARCH_URL, wait_until="networkidle", timeout=60_000)

            page.click(_DEBTOR_RADIO_SELECTOR)
            page.wait_for_timeout(500)
            page.click(_ORG_RADIO_SELECTOR)
            page.wait_for_timeout(300)

            org_field = page.locator(_ORG_NAME_SELECTOR)
            if org_field.count() == 0:
                raise RuntimeError(
                    f"Could not find Organization Name field on {NY_UCC_SEARCH_URL}. "
                    "The portal may have been redesigned."
                )
            org_field.fill(company_name)

            page.click(_SEARCH_BUTTON_SELECTOR)
            page.wait_for_load_state("networkidle", timeout=30_000)
            page.wait_for_timeout(1000)

            return page.content()
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cell(cells: list[str], index: int) -> str | None:
    if index < len(cells):
        value = cells[index].strip()
        return value if value else None
    return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip().split(" ")[0]
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _canonical_filing_type(lien_subtype: str | None) -> str:
    if not lien_subtype:
        return "UCC1"
    text = normalize_ucc_name(lien_subtype)
    if "TERMINAT" in text or "RELEASE" in text:
        return "UCC3"
    if "CONTINUAT" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _canonical_status(lien_status: str | None) -> str:
    if not lien_status:
        return "ACTIVE"
    text = lien_status.upper()
    if text == "ACTIVE":
        return "ACTIVE"
    if text in {"RELEASED", "TERMINATED", "WITHDRAWN", "PURGED", "LAPSED", "INACTIVE"}:
        return "TERMINATED"
    return text


def _confidence(query_normalized: str, debtor_name: str) -> int:
    if not debtor_name:
        return 50
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and debtor_normalized.startswith(query_normalized):
        return 95
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    q_tokens = set(query_normalized.split())
    d_tokens = set(debtor_normalized.split())
    if q_tokens and d_tokens:
        overlap = len(q_tokens & d_tokens) / max(len(q_tokens), len(d_tokens))
        return max(50, int(overlap * 85))
    return 50


def _split_address(address: str | None) -> tuple[str | None, str | None, str | None]:
    """Best-effort parse of 'City, ST  ZIP' from a debtor address string."""
    if not address:
        return None, None, None
    lines = [line.strip() for line in address.replace("\r", "\n").split("\n") if line.strip()]
    last = lines[-1] if lines else ""
    m = re.search(r",\s*([A-Za-z ]+),\s*([A-Z]{2}),?\s+(\d{5}(?:-\d{4})?)", last)
    if m:
        return m.group(1).strip(), m.group(2), m.group(3)
    return None, None, None


# ---------------------------------------------------------------------------
# HTML parser for results table
# ---------------------------------------------------------------------------

class _ResultsTableParser(HTMLParser):
    """Parse the UCC search results table (id="xhtml_grid") from the NY portal HTML."""

    def __init__(self) -> None:
        super().__init__()
        self._in_results_table = False
        self._in_cell = False
        self._depth = 0
        self._current_cell: list[str] = []
        self._current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "table":
            table_id = values.get("id", "")
            if table_id == "xhtml_grid" or self._in_results_table:
                self._depth += 1
                self._in_results_table = True
        elif self._in_results_table and tag == "tr":
            self._current_row = []
        elif self._in_results_table and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if self._in_results_table and tag in {"td", "th"} and self._in_cell:
            self._current_row.append(" ".join(self._current_cell).strip())
            self._in_cell = False
        elif self._in_results_table and tag == "tr" and self._current_row:
            self.rows.append(self._current_row)
            self._current_row = []
        elif tag == "table" and self._in_results_table:
            self._depth -= 1
            if self._depth <= 0:
                self._in_results_table = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if self._in_cell and text:
            self._current_cell.append(text)
