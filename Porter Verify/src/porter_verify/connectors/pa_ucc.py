"""Targeted Pennsylvania UCC public-search connector.

Pennsylvania UCC filings are managed by the PA Department of State at
https://file.dos.pa.gov/search/ucc.  No bulk download or Socrata dataset
exists; the portal charges $12/debtor for certified searches (paper UCC11
form) but provides free, non-certified public lookups via a JavaScript SPA.

CONFIRMED BLOCKED (2026-07-03, live test): the search page is behind
Cloudflare bot-management -- a real Playwright/Chromium session gets a 403
"Performing security verification" Cloudflare challenge page (with a Ray ID
and a `__cf_chl_rt_tk=...` query param), the same class of block confirmed
for apps.azsos.gov (AZ) and sosnc.gov (NC). The XHR-probe fallback below
also cannot succeed since the same Cloudflare edge blocks non-browser
traffic before it reaches any backend API.

Implementation strategy
-----------------------
1. **XHR probe** – the SPA likely calls an internal REST endpoint that we can
   hit directly with httpx (no browser needed).  We attempt this first; if the
   endpoint returns a recognisable JSON payload we parse it and return.
2. **Playwright fallback** – if the XHR probe fails (endpoint requires a
   session token, CSRF header, or the URL has changed), we fall back to a
   headed-less Playwright session that navigates the SPA, types the debtor
   name, waits for results, then reads the rendered DOM. This now raises
   PaUccBlockedError specifically when Cloudflare's challenge is detected,
   rather than a generic RuntimeError.

Both paths produce ``PaUccSearchResult`` dataclasses that are converted to
``PublicSearchUccResult`` by ``to_public_search_results``.

Usage
-----
    from porter_verify.connectors.pa_ucc import search_pa_ucc, to_public_search_results
    rows = search_pa_ucc("ACME CORP")
    results = to_public_search_results("ACME CORP", rows)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any

import httpx

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

PA_UCC_SEARCH_URL = "https://file.dos.pa.gov/search/ucc"

# The SPA may dispatch XHR calls to one of these candidate API paths.
# We probe each in order; if none returns parseable JSON we fall back to
# Playwright.  These paths were derived by inspecting the SPA's network
# traffic as of April 2026 – update if the backend changes.
_XHR_CANDIDATES: list[str] = [
    "https://file.dos.pa.gov/api/ucc/search",
    "https://file.dos.pa.gov/api/search/ucc",
    "https://file.dos.pa.gov/ucc/api/search",
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": PA_UCC_SEARCH_URL,
}

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaUccSearchResult:
    debtor_name: str
    filing_number: str
    secured_party: str | None
    status: str            # e.g. "Active", "Lapsed", "Terminated"
    filing_date: date | None
    lapse_date: date | None
    filing_type: str       # e.g. "UCC1 FINANCING STATEMENT"


# ---------------------------------------------------------------------------
# Public search entry-point
# ---------------------------------------------------------------------------


def search_pa_ucc(
    company_name: str,
    *,
    include_lapsed: bool = False,
) -> list[PaUccSearchResult]:
    """Search the PA DOS UCC portal for ``company_name`` as organisation debtor.

    Tries the XHR API first; falls back to Playwright browser automation when
    the API probe does not succeed.

    Args:
        company_name: Organisation debtor name to search.
        include_lapsed: When *True*, include lapsed/terminated filings.

    Returns:
        List of ``PaUccSearchResult`` (may be empty if no filings found).

    Raises:
        RuntimeError: If both the XHR probe and the Playwright fallback fail.
    """
    log.info("PA UCC search: %r (include_lapsed=%s)", company_name, include_lapsed)

    # 1. Try XHR probe
    try:
        results = _xhr_search(company_name, include_lapsed=include_lapsed)
        log.info("PA UCC XHR probe succeeded: %d results", len(results))
        return results
    except _XhrProbeFailure as exc:
        log.info("PA UCC XHR probe failed (%s); falling back to Playwright", exc)

    # 2. Playwright fallback
    try:
        results = _playwright_search(company_name, include_lapsed=include_lapsed)
        log.info("PA UCC Playwright search succeeded: %d results", len(results))
        return results
    except PaUccBlockedError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"PA UCC search failed for {company_name!r}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# to_public_search_results – matches the pattern from new_jersey_ucc / idaho_ucc
# ---------------------------------------------------------------------------


def to_public_search_results(
    company_name: str,
    rows: list[PaUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert raw search rows into the shared ``PublicSearchUccResult`` format."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    return [
        PublicSearchUccResult(
            state="PA",
            filing_id=row.filing_number,
            debtor_name=row.debtor_name,
            filing_type=_filing_type(row.filing_type),
            status=_status(row.status, row.lapse_date),
            search_query=query,
            source_url=PA_UCC_SEARCH_URL,
            secured_party_name=row.secured_party,
            filing_date=row.filing_date,
            collateral_description="Pennsylvania public UCC status-search summary",
            match_confidence=_confidence(query_normalized, row.debtor_name),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# XHR probe
# ---------------------------------------------------------------------------


class _XhrProbeFailure(Exception):
    """Raised when no XHR candidate endpoint returned parseable UCC JSON."""


class PaUccBlockedError(RuntimeError):
    """Raised when Cloudflare bot-management rejects the PA UCC search request."""


def _xhr_search(
    company_name: str,
    *,
    include_lapsed: bool = False,
) -> list[PaUccSearchResult]:
    """Attempt a direct REST call to the SPA's internal API.

    The PA DOS SPA was built with a backend API; if that API is reachable
    without a browser session token we can skip Playwright entirely.  We try
    each candidate URL with both GET and POST, parsing any JSON that looks
    like a UCC result list.

    Raises:
        _XhrProbeFailure: when all candidates fail.
    """
    lapse_filter = "ALL" if include_lapsed else "UNLAPSED"
    payload = {
        "debtorName": company_name,
        "searchType": "1a",          # organisation name
        "filingStatus": lapse_filter,
        "searchBy": "debtorName",
    }
    params = {
        "debtorName": company_name,
        "searchType": "1a",
        "filingStatus": lapse_filter,
        "searchBy": "debtorName",
    }

    with httpx.Client(
        follow_redirects=True,
        timeout=30,
        headers=_HEADERS,
    ) as client:
        for base_url in _XHR_CANDIDATES:
            # Try GET
            try:
                resp = client.get(base_url, params=params)
                if resp.status_code == 200:
                    parsed = _parse_xhr_response(resp)
                    if parsed is not None:
                        return parsed
            except httpx.TransportError:
                pass

            # Try POST (JSON body)
            try:
                resp = client.post(
                    base_url,
                    json=payload,
                    headers={**_HEADERS, "Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    parsed = _parse_xhr_response(resp)
                    if parsed is not None:
                        return parsed
            except httpx.TransportError:
                pass

    raise _XhrProbeFailure("no candidate XHR endpoint succeeded")


def _parse_xhr_response(resp: httpx.Response) -> list[PaUccSearchResult] | None:
    """Return parsed results if the response looks like a UCC result list, else None."""
    try:
        data = resp.json()
    except (json.JSONDecodeError, ValueError):
        return None

    # The API might return {"results": [...]} or a bare list
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        # Try common envelope keys
        for key in ("results", "data", "filings", "records", "items"):
            if key in data and isinstance(data[key], list):
                rows = data[key]
                break
        else:
            return None
    else:
        return None

    if not rows:
        # Empty list is a valid (no results) response – return empty list
        # only if the response explicitly looks like a UCC API response
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            return []
        return None

    results: list[PaUccSearchResult] = []
    for row in rows:
        result = _result_from_xhr_row(row)
        if result is not None:
            results.append(result)
    return results if results else None


def _result_from_xhr_row(row: Any) -> PaUccSearchResult | None:
    """Map a raw API dict to a ``PaUccSearchResult``.

    Field names are guesses based on PA DOS conventions and similar state APIs;
    we attempt several plausible key names for each field.
    """
    if not isinstance(row, dict):
        return None

    def _get(*keys: str) -> str:
        for k in keys:
            v = row.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
        return ""

    filing_number = _get(
        "filingNumber", "filing_number", "fileNumber", "id", "filingId", "FILING_NUMBER"
    )
    if not filing_number:
        return None

    debtor_name = _get(
        "debtorName", "debtor_name", "debtorOrganizationName", "DEBTOR_NAME", "debtor"
    )
    secured_party = _get(
        "securedPartyName", "secured_party", "securedParty", "SECURED_PARTY"
    ) or None
    status = _get("status", "filingStatus", "STATUS") or "ACTIVE"
    filing_date_raw = _get("filingDate", "filing_date", "dateOfFiling", "FILE_DATE")
    lapse_date_raw = _get("lapseDate", "lapse_date", "expirationDate", "LAPSE_DATE")
    filing_type = _get("filingType", "filing_type", "type", "FILING_TYPE") or "UCC1 FINANCING STATEMENT"

    return PaUccSearchResult(
        debtor_name=debtor_name,
        filing_number=filing_number,
        secured_party=secured_party,
        status=status,
        filing_date=_parse_date(filing_date_raw),
        lapse_date=_parse_date(lapse_date_raw),
        filing_type=filing_type,
    )


# ---------------------------------------------------------------------------
# Playwright fallback
# ---------------------------------------------------------------------------


def _playwright_search(
    company_name: str,
    *,
    include_lapsed: bool = False,
) -> list[PaUccSearchResult]:
    """Drive the PA DOS SPA with Playwright to perform a debtor-name search.

    This function requires ``playwright`` to be installed:
        pip install playwright
        playwright install chromium

    It navigates to the UCC search page, fills in the organisation name,
    submits, waits for the results table to appear, then captures the DOM
    HTML for offline parsing.

    Args:
        company_name: Organisation debtor name to search.
        include_lapsed: When *True*, look for an "Include Lapsed" toggle.

    Returns:
        List of ``PaUccSearchResult``.

    Raises:
        ImportError: If playwright is not installed.
        RuntimeError: If the search page does not load or results do not appear.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "playwright is required for PA UCC search; install with: "
            "pip install playwright && playwright install chromium"
        ) from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        # Intercept XHR calls so we can capture the raw API response if the
        # SPA makes one – this avoids parsing the DOM entirely.
        captured_api_responses: list[Any] = []

        def _on_response(response: Any) -> None:
            url = response.url
            if "ucc" in url.lower() and "search" in url.lower():
                try:
                    body = response.json()
                    captured_api_responses.append(body)
                except Exception:  # noqa: BLE001
                    pass

        page.on("response", _on_response)

        try:
            response = page.goto(
                PA_UCC_SEARCH_URL, wait_until="domcontentloaded", timeout=30_000
            )
            page.wait_for_timeout(2000)
            if (response is not None and response.status == 403) or (
                "__cf_chl_rt_tk" in page.url
            ):
                raise PaUccBlockedError(
                    "PA DOS UCC search is blocked by Cloudflare bot-management "
                    "(403 with a Cloudflare challenge redirect). Route to manual "
                    "review."
                )

            # --- Locate the organisation name input ---
            # The SPA renders a text input; we try a range of selectors that
            # cover common React/Angular patterns used by PA DOS portals.
            org_input_selectors = [
                "input[name='debtorName']",
                "input[placeholder*='debtor' i]",
                "input[placeholder*='organization' i]",
                "input[id*='debtor' i]",
                "input[id*='organization' i]",
                "input[aria-label*='debtor' i]",
                "input[aria-label*='organization' i]",
                "#debtorName",
                "#organizationName",
                "input[type='text']:first-of-type",
            ]
            org_input = None
            for selector in org_input_selectors:
                try:
                    org_input = page.wait_for_selector(selector, timeout=5_000)
                    if org_input:
                        break
                except Exception:  # noqa: BLE001
                    continue

            if org_input is None:
                raise RuntimeError(
                    "Could not locate the debtor name input on the PA UCC search page. "
                    "The SPA layout may have changed; inspect the live page and update "
                    "the selector list in pa_ucc._playwright_search."
                )

            # Clear any pre-filled value and type the search term
            org_input.triple_click()
            org_input.type(company_name, delay=50)

            # --- Include lapsed toggle (optional) ---
            if include_lapsed:
                lapsed_selectors = [
                    "input[type='checkbox'][id*='lapse' i]",
                    "input[type='checkbox'][name*='lapse' i]",
                    "label[for*='lapse' i]",
                ]
                for sel in lapsed_selectors:
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        break

            # --- Submit ---
            submit_selectors = [
                "button[type='submit']",
                "button:has-text('Search')",
                "input[type='submit']",
                "[role='button']:has-text('Search')",
            ]
            submitted = False
            for sel in submit_selectors:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    submitted = True
                    break
            if not submitted:
                # Fall back to pressing Enter in the input
                org_input.press("Enter")

            # --- Wait for results ---
            # The SPA will either render a table, a list, or show "No results".
            results_selectors = [
                "table",
                "[class*='results' i]",
                "[class*='result-list' i]",
                "[class*='filing' i]",
                "td",
            ]
            for sel in results_selectors:
                try:
                    page.wait_for_selector(sel, timeout=15_000)
                    break
                except Exception:  # noqa: BLE001
                    continue

            # Small extra wait for the SPA to finish rendering
            page.wait_for_timeout(2_000)

            # --- Prefer captured API response (most reliable) ---
            for body in captured_api_responses:
                parsed = _parse_xhr_response_body(body)
                if parsed is not None:
                    return parsed

            # --- Fall back to DOM parsing ---
            html = page.content()
            return _parse_dom_results(html)

        finally:
            context.close()
            browser.close()


def _parse_xhr_response_body(body: Any) -> list[PaUccSearchResult] | None:
    """Parse a captured XHR response body (already decoded from JSON)."""
    if isinstance(body, list):
        rows = body
    elif isinstance(body, dict):
        for key in ("results", "data", "filings", "records", "items"):
            if key in body and isinstance(body[key], list):
                rows = body[key]
                break
        else:
            return None
    else:
        return None

    results: list[PaUccSearchResult] = []
    for row in rows:
        result = _result_from_xhr_row(row)
        if result is not None:
            results.append(result)
    return results


# ---------------------------------------------------------------------------
# DOM parser for Playwright-rendered HTML
# ---------------------------------------------------------------------------


def _parse_dom_results(html: str) -> list[PaUccSearchResult]:
    """Parse the rendered SPA HTML for a results table.

    The PA DOS SPA renders UCC results in an HTML table.  Column ordering is
    based on the typical layout:
        0: Filing Number
        1: Debtor Name
        2: Secured Party
        3: Filing Date
        4: Lapse Date
        5: Status
        6: Filing Type

    Column indices may shift; we attempt to detect headers first and map them.
    """
    parser = _TableParser()
    parser.feed(html)

    if not parser.rows:
        return []

    # Detect header row to determine column mapping
    col_map = _detect_column_map(parser.rows)

    results: list[PaUccSearchResult] = []
    for row in parser.rows:
        # Skip rows that look like headers
        row_lower = [c.lower() for c in row]
        if any(h in row_lower for h in ("filing number", "debtor name", "status")):
            continue

        # Require at least a filing number column
        filing_col = col_map.get("filing_number", 0)
        if filing_col >= len(row):
            continue
        filing_number = row[filing_col].strip()
        if not filing_number:
            continue

        def _col(key: str, fallback: int) -> str:
            idx = col_map.get(key, fallback)
            return row[idx].strip() if idx < len(row) else ""

        results.append(
            PaUccSearchResult(
                filing_number=filing_number,
                debtor_name=_col("debtor_name", 1),
                secured_party=_col("secured_party", 2) or None,
                filing_date=_parse_date(_col("filing_date", 3)),
                lapse_date=_parse_date(_col("lapse_date", 4)),
                status=_col("status", 5) or "ACTIVE",
                filing_type=_col("filing_type", 6) or "UCC1 FINANCING STATEMENT",
            )
        )
    return results


def _detect_column_map(rows: list[list[str]]) -> dict[str, int]:
    """Scan the first few rows for a header row and return a column-name mapping."""
    keyword_map = {
        "filing number": "filing_number",
        "filing no": "filing_number",
        "file number": "filing_number",
        "debtor": "debtor_name",
        "secured party": "secured_party",
        "secured": "secured_party",
        "filing date": "filing_date",
        "file date": "filing_date",
        "lapse date": "lapse_date",
        "expiration": "lapse_date",
        "status": "status",
        "type": "filing_type",
        "filing type": "filing_type",
    }
    for row in rows[:3]:
        mapping: dict[str, int] = {}
        for idx, cell in enumerate(row):
            cell_lower = cell.strip().lower()
            for keyword, field in keyword_map.items():
                if keyword in cell_lower and field not in mapping:
                    mapping[field] = idx
        if mapping:
            return mapping
    # No header found – return empty dict (callers use hardcoded fallback indices)
    return {}


class _TableParser(HTMLParser):
    """Minimal HTML table parser that collects all <tr>/<td>/<th> text."""

    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.current_row = []
        elif tag in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.in_cell:
            self.current_row.append(" ".join(self.current_cell).strip())
            self.in_cell = False
        elif tag == "tr" and self.current_row:
            self.rows.append(self.current_row)
            self.current_row = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            text = data.strip()
            if text:
                self.current_cell.append(text)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _filing_type(raw: str) -> str:
    text = normalize_ucc_name(raw)
    if "TERMIN" in text or "RELEASE" in text:
        return "UCC3"
    if "AMEND" in text:
        return "AMENDMENT"
    if "CONTINU" in text:
        return "CONTINUATION"
    return "UCC1"


def _status(raw: str, lapse_date: date | None) -> str:
    text = normalize_ucc_name(raw)
    if "TERMINATED" in text or "RELEASED" in text:
        return "TERMINATED"
    if "LAPSED" in text or "LAPSE" in text:
        return "TERMINATED"
    if lapse_date and lapse_date < datetime.utcnow().date():
        return "TERMINATED"
    if "ACTIVE" in text or "FILED" in text or "OPEN" in text:
        return "ACTIVE"
    return raw.upper() if raw else "ACTIVE"


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    return 70


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None
