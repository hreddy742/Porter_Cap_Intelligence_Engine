"""Targeted North Carolina UCC public-search connector.

CONFIRMED BLOCKED (2026-07-03, live test): sosnc.gov is behind Cloudflare
bot-management -- a real headless Chromium session via Playwright receives
HTTP 403 with a Cloudflare challenge redirect (`__cf_chl_rt_tk=...` query
param appended to the URL), the same class of block confirmed for
apps.azsos.gov. This is not a wrong selector or field name; the page never
renders far enough to reach the search form.

Bulk data is available via a paid FTP subscription from NC SOS
($4,000-$5,200/year). Until that contract is in place, and until Cloudflare
bot-management is bypassed (stealth browser fingerprinting or a paid
anti-bot service -- out of scope here), there is no working path to NC UCC
data. search_nc_ucc() raises NcUccBlockedError so callers can route to
manual review instead of silently returning an empty result set.

Usage:
    results = search_nc_ucc("Acme Widgets LLC")
    public  = to_public_search_results("Acme Widgets LLC", results)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

NC_UCC_SEARCH_URL = (
    "https://www.sosnc.gov/online_services/search/by_title/_uniform_commercial_code"
)
NC_UCC_RESULTS_URL = (
    "https://www.sosnc.gov/online_services/search/Uniform_Commercial_Code_results_Desk"
)

# Minimum gap between consecutive searches (seconds).  NC ToS requires
# restrained use; 5 s is a conservative floor.
_MIN_REQUEST_GAP_S: float = 5.0
_last_request_ts: float = 0.0


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


class NcUccBlockedError(RuntimeError):
    """Raised when Cloudflare bot-management rejects the NC UCC search request."""


@dataclass(frozen=True)
class NcUccSearchResult:
    """One row returned by the NC SOS UCC search."""

    filing_number: str
    debtor_name: str
    filing_type: str
    status: str
    filing_date: date | None
    lapse_date: date | None
    secured_party_name: str | None
    collateral_description: str | None
    debtor_city: str | None
    debtor_state: str | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def search_nc_ucc(
    company_name: str,
    *,
    search_mode: str = "all words",
) -> list[NcUccSearchResult]:
    """Search NC SOS UCC filings for *company_name*.

    *search_mode* maps to the Non-standard RA9 sub-option:
      "starting with" | "any words" | "all words" |
      "exact match"   | "sounds like"

    Requires ``playwright`` to be installed::

        pip install playwright
        playwright install chromium

    Raises ``RuntimeError`` if Playwright is not available.
    Raises ``playwright.sync_api.Error`` on page-level failures.
    """
    _rate_limit()
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "playwright is required for NC UCC search. "
            "Install with: pip install playwright && playwright install chromium"
        ) from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        try:
            response = page.goto(
                NC_UCC_SEARCH_URL, wait_until="domcontentloaded", timeout=30_000
            )
            if (response is not None and response.status == 403) or (
                "__cf_chl_rt_tk" in page.url
            ):
                raise NcUccBlockedError(
                    "NC SOS UCC search is blocked by Cloudflare bot-management "
                    "(403 with a Cloudflare challenge redirect). Route to manual "
                    "review."
                )

            # --- locate and fill the debtor name field ---
            # The form field name is not publicly documented.  We try a set of
            # known selector patterns observed via DevTools inspection.
            name_selectors = [
                'input[name*="debtor" i]',
                'input[name*="Debtor" ]',
                'input[id*="debtor" i]',
                'input[placeholder*="debtor" i]',
                'input[placeholder*="name" i]',
                'input[type="text"]',  # fallback: first visible text input
            ]
            name_field = None
            for sel in name_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=1_000):
                        name_field = el
                        break
                except Exception:  # noqa: BLE001
                    continue

            if name_field is None:
                raise RuntimeError(
                    "NC UCC: could not locate the debtor name input on "
                    f"{NC_UCC_SEARCH_URL}. The form structure may have changed."
                )

            name_field.fill(company_name)

            # --- select Non-standard RA9 search type if a radio/select exists ---
            _try_select_nonstandard_ra9(page)

            # --- select the match mode sub-option ---
            _try_select_match_mode(page, search_mode)

            # --- submit the form ---
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("Search")',
                'input[value*="Search" i]',
            ]
            submitted = False
            for sel in submit_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=1_000):
                        btn.click()
                        submitted = True
                        break
                except Exception:  # noqa: BLE001
                    continue

            if not submitted:
                raise RuntimeError(
                    "NC UCC: could not find a submit button on "
                    f"{NC_UCC_SEARCH_URL}. The form structure may have changed."
                )

            page.wait_for_load_state("networkidle", timeout=30_000)
            html = page.content()
        finally:
            context.close()
            browser.close()

    _update_last_request_ts()
    return parse_nc_ucc_results(html)


def to_public_search_results(
    company_name: str,
    rows: list[NcUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert raw NC search rows to the platform-standard PublicSearchUccResult list."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    return [
        PublicSearchUccResult(
            state="NC",
            filing_id=row.filing_number,
            debtor_name=row.debtor_name,
            filing_type=row.filing_type,
            status=row.status,
            search_query=query,
            source_url=NC_UCC_SEARCH_URL,
            filing_date=row.filing_date,
            debtor_city=row.debtor_city,
            debtor_state=row.debtor_state,
            collateral_description=row.collateral_description,
            secured_party_name=row.secured_party_name,
            match_confidence=_confidence(query_normalized, row.debtor_name),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


def parse_nc_ucc_results(html: str) -> list[NcUccSearchResult]:
    """Parse the NC SOS results page HTML into NcUccSearchResult objects.

    The results page renders an HTML ``<table>`` at the
    ``Uniform_Commercial_Code_results_Desk`` endpoint.  Column order is
    inferred from header text — making the parser robust to minor column
    reordering.
    """
    parser = _NcResultsTableParser()
    parser.feed(html)

    if not parser.rows:
        return []

    # First row is the header row; derive column index map from it.
    header = [cell.lower() for cell in parser.rows[0]]
    col = _column_map(header)

    results: list[NcUccSearchResult] = []
    for cells in parser.rows[1:]:
        if len(cells) < 2:
            continue
        filing_number = _cell(cells, col.get("filing_number"))
        debtor_name = _cell(cells, col.get("debtor_name"))
        if not filing_number and not debtor_name:
            continue
        filing_type_raw = _cell(cells, col.get("filing_type")) or "UCC1"
        status_raw = _cell(cells, col.get("status")) or "ACTIVE"
        results.append(
            NcUccSearchResult(
                filing_number=filing_number or "",
                debtor_name=debtor_name or "",
                filing_type=_normalize_filing_type(filing_type_raw),
                status=_normalize_status(status_raw, filing_type_raw),
                filing_date=_parse_date(_cell(cells, col.get("filing_date"))),
                lapse_date=_parse_date(_cell(cells, col.get("lapse_date"))),
                secured_party_name=_cell(cells, col.get("secured_party")),
                collateral_description=_cell(cells, col.get("collateral")),
                debtor_city=_cell(cells, col.get("debtor_city")),
                debtor_state=_cell(cells, col.get("debtor_state")),
            )
        )
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _rate_limit() -> None:
    global _last_request_ts  # noqa: PLW0603
    elapsed = time.monotonic() - _last_request_ts
    if elapsed < _MIN_REQUEST_GAP_S:
        time.sleep(_MIN_REQUEST_GAP_S - elapsed)


def _update_last_request_ts() -> None:
    global _last_request_ts  # noqa: PLW0603
    _last_request_ts = time.monotonic()


def _try_select_nonstandard_ra9(page: object) -> None:
    """Attempt to select Non-standard RA9 search type on the form."""
    # Try common patterns: radio buttons, select dropdowns.
    selectors = [
        'input[type="radio"][value*="non" i]',
        'input[type="radio"][value*="nonstandard" i]',
        'input[type="radio"][id*="nonstandard" i]',
        'select[name*="search" i]',
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=500):
                tag = el.evaluate("e => e.tagName.toLowerCase()")
                if tag == "select":
                    # pick the non-standard option
                    el.select_option(label="Non-standard")
                else:
                    el.click()
                return
        except Exception:  # noqa: BLE001
            continue


def _try_select_match_mode(page: object, mode: str) -> None:
    """Attempt to set the Non-standard RA9 sub-option (match mode)."""
    mode_selectors = [
        f'input[type="radio"][value*="{mode}" i]',
        f'select option:has-text("{mode}")',
    ]
    for sel in mode_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=500):
                tag = el.evaluate("e => e.tagName.toLowerCase()")
                if tag == "option":
                    # select the parent <select>
                    page.locator(sel).locator("xpath=..").select_option(label=mode)
                else:
                    el.click()
                return
        except Exception:  # noqa: BLE001
            continue


def _column_map(header_cells: list[str]) -> dict[str, int]:
    """Map logical column names to positional indices from the header row."""
    mapping: dict[str, int] = {}
    keywords: dict[str, list[str]] = {
        "filing_number": ["filing number", "file number", "ucc number", "number"],
        "debtor_name": ["debtor name", "debtor", "organization", "name"],
        "filing_type": ["type", "filing type"],
        "status": ["status", "lien status"],
        "filing_date": ["filing date", "date filed", "filed"],
        "lapse_date": ["lapse date", "lapse", "expiration"],
        "secured_party": ["secured party", "secured", "lender", "creditor"],
        "collateral": ["collateral", "description"],
        "debtor_city": ["city"],
        "debtor_state": ["state"],
    }
    for col_name, kws in keywords.items():
        for i, cell in enumerate(header_cells):
            for kw in kws:
                if kw in cell and col_name not in mapping:
                    mapping[col_name] = i
    return mapping


def _cell(cells: list[str], index: int | None) -> str | None:
    if index is None or index >= len(cells):
        return None
    value = cells[index].strip()
    return value if value else None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _normalize_filing_type(value: str) -> str:
    text = normalize_ucc_name(value)
    if "TERMIN" in text or "RELEASE" in text or "DISCHARGE" in text:
        return "UCC3"
    if "CONTINUATION" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _normalize_status(value: str, filing_type_raw: str) -> str:
    text = normalize_ucc_name(value)
    ft_text = normalize_ucc_name(filing_type_raw)
    if "TERMIN" in text or "LAPSED" in text or "RELEASE" in text:
        return "TERMINATED"
    if "TERMIN" in ft_text or "RELEASE" in ft_text:
        return "TERMINATED"
    return "ACTIVE"


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    if query_normalized and debtor_normalized and query_normalized.split()[0] in debtor_normalized:
        return 75
    return 60


# ---------------------------------------------------------------------------
# HTML table parser
# ---------------------------------------------------------------------------


class _NcResultsTableParser(HTMLParser):
    """Extract all rows from the first ``<table>`` on the results page."""

    def __init__(self) -> None:
        super().__init__()
        self._in_table: bool = False
        self._in_cell: bool = False
        self._current_cell: list[str] = []
        self._current_row: list[str] = []
        self.rows: list[list[str]] = []
        self._table_depth: int = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._in_table = True
        elif self._in_table and tag == "tr":
            self._current_row = []
        elif self._in_table and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self._table_depth -= 1
            if self._table_depth == 0:
                self._in_table = False
        elif self._in_table and tag in {"td", "th"} and self._in_cell:
            self._current_row.append(" ".join(self._current_cell).strip())
            self._in_cell = False
        elif self._in_table and tag == "tr" and self._current_row:
            self.rows.append(self._current_row)
            self._current_row = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if self._in_cell and text:
            self._current_cell.append(text)
