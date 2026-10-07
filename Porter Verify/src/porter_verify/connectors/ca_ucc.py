"""Targeted California UCC public-search connector.

CA UCC filings are served through a JavaScript SPA at:
  https://bizfileonline.sos.ca.gov/search/ucc

There is NO public Socrata/bulk dataset — bulk downloads require a
paid, authenticated SOS account ($100-$900).

CONFIRMED BLOCKED (2026-07-03, live test): the search page is protected by
Imperva Incapsula bot-management. A real headless Chromium session via
Playwright gets redirected into an "_Incapsula_Resource" challenge iframe
-- the actual React app never renders (body innerHTML is only ~526 bytes,
vs. the real app's full search form). This was confirmed by inspecting
page.frames(): a bizfileonline.sos.ca.gov/_Incapsula_Resource?... frame is
present instead of the search UI. The real selectors below
(input[aria-label="Search by name or file number"],
button[aria-label="Execute search"]) were captured correctly during a
brief window before Incapsula's challenge replaced the DOM, confirming
this is a bot-block, not a wrong selector.

Bypassing Incapsula would require browser-fingerprint evasion or a paid
anti-bot bypass service -- out of scope here. search_ca_ucc() raises
CaUccBlockedError so callers can route to manual review instead of
silently returning an empty result set.

Playwright must be installed in the project environment (needed if
Incapsula bot-management is ever bypassed and this connector is
reactivated):
  pip install playwright
  playwright install chromium
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

CA_UCC_SEARCH_URL = "https://bizfileonline.sos.ca.gov/search/ucc"

# Real selectors (confirmed live 2026-07-03, briefly, before Incapsula's
# challenge replaced the DOM). Kept accurate for when the block is lifted.
_DEBTOR_INPUT_SELECTOR = "input[aria-label='Search by name or file number']"
_SEARCH_BUTTON_SELECTOR = "button[aria-label='Execute search']"
_RESULTS_TABLE_SELECTOR = "table.results-table, table[class*='result' i], div[class*='grid' i] table"
_NO_RESULTS_TEXT = "no results"
_PAGE_LOAD_TIMEOUT = 30_000   # ms
_SEARCH_TIMEOUT = 20_000      # ms
_MAX_PAGES = 10               # guard against infinite pagination


class CaUccBlockedError(RuntimeError):
    """Raised when Incapsula bot-management rejects the CA UCC search request."""


@dataclass(frozen=True)
class CaliforniaUccSearchResult:
    filing_number: str
    debtor_name: str
    debtor_address: str | None
    secured_party_name: str | None
    filing_date: date | None
    lapse_date: date | None
    status: str
    filing_type: str


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def search_ca_ucc(company_name: str) -> list[CaliforniaUccSearchResult]:
    """Search CA BizFile UCC for *company_name* and return parsed results.

    Requires Playwright with Chromium installed.  Falls back to an empty
    list (with a warning) if Playwright is unavailable so the rest of the
    application keeps running.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError as exc:
        import warnings
        warnings.warn(
            "Playwright is not installed; CA UCC search is unavailable. "
            "Run: pip install playwright && playwright install chromium",
            RuntimeWarning,
            stacklevel=2,
        )
        raise RuntimeError("Playwright required for CA UCC search") from exc

    results: list[CaliforniaUccSearchResult] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.goto(CA_UCC_SEARCH_URL, wait_until="domcontentloaded", timeout=_PAGE_LOAD_TIMEOUT)
            page.wait_for_timeout(3000)

            if any("_Incapsula_Resource" in frame.url for frame in page.frames):
                raise CaUccBlockedError(
                    "CA BizFile UCC search is blocked by Incapsula bot-management "
                    "(an _Incapsula_Resource challenge frame was returned instead "
                    "of the search app). Route to manual review."
                )

            # Ensure the Debtor tab is active (it usually is by default)
            _click_debtor_tab_if_needed(page)
            # Fill and submit the search form
            debtor_input = page.locator(_DEBTOR_INPUT_SELECTOR).first
            debtor_input.wait_for(timeout=_PAGE_LOAD_TIMEOUT)
            debtor_input.fill(company_name)
            page.locator(_SEARCH_BUTTON_SELECTOR).first.click()
            # Wait for results to render
            page.wait_for_load_state("networkidle", timeout=_SEARCH_TIMEOUT)
            # Collect paginated results
            page_num = 0
            while page_num < _MAX_PAGES:
                html = page.content()
                if _no_results(html):
                    break
                page_results = _parse_results_from_html(html)
                results.extend(page_results)
                if not page_results or not _go_to_next_page(page):
                    break
                page_num += 1
                time.sleep(0.5)  # polite crawl delay
        finally:
            browser.close()
    return results


def to_public_search_results(
    company_name: str,
    rows: list[CaliforniaUccSearchResult],
) -> list[PublicSearchUccResult]:
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    mapped: list[PublicSearchUccResult] = []
    for row in rows:
        mapped.append(
            PublicSearchUccResult(
                state="CA",
                filing_id=row.filing_number,
                debtor_name=row.debtor_name,
                filing_type=_canonical_filing_type(row.filing_type),
                status=_canonical_status(row.status, row.filing_type),
                search_query=query,
                source_url=CA_UCC_SEARCH_URL,
                filing_date=row.filing_date,
                termination_date=row.lapse_date,
                debtor_address=row.debtor_address,
                debtor_city=_city_from_address(row.debtor_address),
                debtor_state="CA",
                secured_party_name=row.secured_party_name,
                collateral_description=None,
                match_confidence=_confidence(query_normalized, row.debtor_name),
            )
        )
    return mapped


# ---------------------------------------------------------------------------
# HTML parsing (works on the rendered DOM snapshot from Playwright)
# ---------------------------------------------------------------------------

def _parse_results_from_html(html: str) -> list[CaliforniaUccSearchResult]:
    """Extract UCC filing rows from the rendered page HTML."""
    from html.parser import HTMLParser  # noqa: PLC0415

    parser = _CaResultsParser()
    parser.feed(html)
    results: list[CaliforniaUccSearchResult] = []
    for cells in parser.rows:
        parsed = _row_to_result(cells)
        if parsed is not None:
            results.append(parsed)
    return results


def _row_to_result(cells: list[str]) -> CaliforniaUccSearchResult | None:
    """Map a list of table cell strings to a CaliforniaUccSearchResult.

    Expected column order (BizFile UCC search results as of 2025):
      0: Filing Number
      1: Debtor Name
      2: Debtor Address  (may be combined city/state/zip)
      3: Secured Party
      4: Filing Date
      5: Lapse Date
      6: Status
      7: Filing Type   (may be absent on some result sets)
    """
    # Skip header rows and rows with too few cells
    if len(cells) < 6:
        return None
    filing_number = cells[0].strip()
    # Heuristic: filing numbers for CA are typically numeric or alphanumeric strings
    if not filing_number or filing_number.lower() in {"filing number", "filing #", "#"}:
        return None
    # Remove any purely numeric header-like values that are actually column indices
    if re.match(r"^[a-z ]+$", filing_number, re.IGNORECASE) and len(filing_number) > 10:
        return None
    return CaliforniaUccSearchResult(
        filing_number=filing_number,
        debtor_name=cells[1].strip() if len(cells) > 1 else "",
        debtor_address=cells[2].strip() if len(cells) > 2 else None,
        secured_party_name=cells[3].strip() if len(cells) > 3 else None,
        filing_date=_parse_date(cells[4]) if len(cells) > 4 else None,
        lapse_date=_parse_date(cells[5]) if len(cells) > 5 else None,
        status=cells[6].strip() if len(cells) > 6 else "ACTIVE",
        filing_type=cells[7].strip() if len(cells) > 7 else "UCC1",
    )


class _CaResultsParser:
    """Lightweight SAX-style parser for CA BizFile results tables."""

    def __init__(self) -> None:
        from html.parser import HTMLParser  # noqa: PLC0415

        class _Inner(HTMLParser):
            def __init__(inner_self) -> None:
                super().__init__()
                inner_self.in_table = False
                inner_self.in_cell = False
                inner_self.cell_buf: list[str] = []
                inner_self.current_row: list[str] = []
                inner_self.rows: list[list[str]] = []

            def handle_starttag(inner_self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                attr_dict = dict(attrs)
                if tag == "table":
                    # Accept any table that has UCC-search-related class names or
                    # accept the first table encountered as a fallback
                    cls = attr_dict.get("class", "") or ""
                    if any(k in cls.lower() for k in ("result", "ucc", "filing", "search", "grid")):
                        inner_self.in_table = True
                    elif not inner_self.in_table:
                        # Fallback: grab the first table on the page
                        inner_self.in_table = True
                elif inner_self.in_table and tag in {"td", "th"}:
                    inner_self.in_cell = True
                    inner_self.cell_buf = []
                elif inner_self.in_table and tag == "tr":
                    inner_self.current_row = []

            def handle_endtag(inner_self, tag: str) -> None:
                if inner_self.in_table:
                    if tag in {"td", "th"} and inner_self.in_cell:
                        inner_self.current_row.append(" ".join(inner_self.cell_buf).strip())
                        inner_self.in_cell = False
                    elif tag == "tr" and inner_self.current_row:
                        inner_self.rows.append(inner_self.current_row)
                        inner_self.current_row = []
                    elif tag == "table":
                        inner_self.in_table = False

            def handle_data(inner_self, data: str) -> None:
                if inner_self.in_cell:
                    text = data.strip()
                    if text:
                        inner_self.cell_buf.append(text)

        self._parser = _Inner()

    def feed(self, html: str) -> None:
        self._parser.feed(html)

    @property
    def rows(self) -> list[list[str]]:
        return self._parser.rows


# ---------------------------------------------------------------------------
# Playwright helpers
# ---------------------------------------------------------------------------

def _click_debtor_tab_if_needed(page) -> None:  # type: ignore[no-untyped-def]
    """Click the 'Debtor' search tab if the page exposes multiple tabs."""
    try:
        debtor_tab = page.locator(
            "button:has-text('Debtor'), [role='tab']:has-text('Debtor'), "
            "a:has-text('Debtor')"
        ).first
        if debtor_tab.is_visible(timeout=3_000):
            debtor_tab.click()
            page.wait_for_load_state("networkidle", timeout=5_000)
    except Exception:  # noqa: BLE001
        pass  # Tab may not exist; proceed with current state


def _no_results(html: str) -> bool:
    return _NO_RESULTS_TEXT in html.lower()


def _go_to_next_page(page) -> bool:  # type: ignore[no-untyped-def]
    """Click the 'Next' pagination button if present and enabled.

    Returns True if navigation happened, False if we are on the last page.
    """
    try:
        next_btn = page.locator(
            "button:has-text('Next'), a:has-text('Next'), "
            "[aria-label*='next' i]:not([disabled])"
        ).first
        if not next_btn.is_visible(timeout=2_000):
            return False
        if next_btn.is_disabled():
            return False
        next_btn.click()
        page.wait_for_load_state("networkidle", timeout=_SEARCH_TIMEOUT)
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _canonical_filing_type(raw: str) -> str:
    text = raw.upper().strip()
    if "TERMIN" in text or "RELEASE" in text:
        return "UCC3"
    if "CONTINUATION" in text or "CONT" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _canonical_status(status: str, filing_type: str) -> str:
    text = status.upper().strip()
    ftype = filing_type.upper().strip()
    if "LAPS" in text or "TERMIN" in text or "RELEAS" in text or "UCC3" in ftype or "TERMIN" in ftype:
        return "TERMINATED"
    if "ACTIVE" in text or "FILED" in text:
        return "ACTIVE"
    return "ACTIVE"


def _city_from_address(address: str | None) -> str | None:
    """Best-effort city extraction from a combined address string."""
    if not address:
        return None
    # Try to extract the city portion before any state abbreviation
    # e.g. "123 Main St, Los Angeles, CA 90001"
    match = re.search(r",\s*([^,]+),\s*[A-Z]{2}\s+\d{5}", address)
    if match:
        return match.group(1).strip()
    # If no state/zip pattern, return None to avoid guessing
    return None


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if not query_normalized:
        return 50
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized in debtor_normalized:
        return 90
    # Partial token overlap
    q_tokens = set(query_normalized.split())
    d_tokens = set(debtor_normalized.split())
    if q_tokens and q_tokens.issubset(d_tokens):
        return 85
    overlap = len(q_tokens & d_tokens)
    if overlap and q_tokens:
        return 60 + min(25, int(25 * overlap / len(q_tokens)))
    return 50
