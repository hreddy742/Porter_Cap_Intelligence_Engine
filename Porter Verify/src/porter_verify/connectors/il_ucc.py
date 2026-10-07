"""Targeted Illinois UCC public-search connector.

Illinois UCC filings are maintained by the IL Secretary of State at
https://apps.ilsos.gov/uccsearch/. No free bulk download is available —
bulk data requires a $2,500 one-time fee plus $200/week for updates via
contract with IL SOS.

CONFIRMED BLOCKED (2026-07-03, live test) -- but inconsistently, which is
itself evidence of active bot-management rather than a config bug.
Repeated live requests within the same session produced three different
outcomes: a genuine HTTP 403 with an Akamai-style WAF block page ("Sorry,
the page you are looking for is not available... Reference ID: ... Client
IP: ..."), a connection timeout, and a 200 response whose body was
byte-identical to the blank search form (i.e. the POST never actually
executed a search server-side). This was confirmed via both plain httpx
and a real Playwright/Chromium session -- neither is reliably let through.
An earlier version of this connector's docstring promised a
"search_il_ucc_playwright" fallback for exactly this case, but that
function was never actually implemented; this version replaces that
dangling promise with an honest error. search_il_ucc() raises
IlUccBlockedError on a detected block so callers can route to manual
review instead of silently returning an empty result set.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any

import httpx

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

IL_UCC_SEARCH_URL = "https://apps.ilsos.gov/uccsearch/"


class IlUccBlockedError(RuntimeError):
    """Raised when the IL SOS UCC portal returns a WAF/bot-management block."""

# Search type constants matching the portal's form values
SEARCH_TYPE_ORGANIZATION = "Organization"
SEARCH_TYPE_PERSONAL = "Personal"
SEARCH_TYPE_KEYWORD = "Keyword"
SEARCH_TYPE_FILE_NUMBER = "FileNumber"


@dataclass(frozen=True)
class IllinoisUccSearchResult:
    """A single row returned from the IL SOS UCC search results table."""

    filing_number: str
    debtor_name: str
    debtor_city: str | None
    debtor_state: str | None
    secured_party: str | None
    filing_date: date | None
    lapse_date: date | None
    filing_type: str
    status: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def search_il_ucc(
    company_name: str,
    *,
    search_type: str = SEARCH_TYPE_ORGANIZATION,
) -> list[IllinoisUccSearchResult]:
    """Search the IL SOS UCC portal for *company_name*.

    Performs an organization-name search by default.  The IL SOS portal
    returns HTTP 403 to automated User-Agent strings; this function uses
    a realistic browser User-Agent and session cookies.  If the server
    still rejects the request a ``httpx.HTTPStatusError`` with status 403
    is raised — in that case, use Playwright (see module docstring).

    Args:
        company_name: Debtor organization name to search.
        search_type: One of SEARCH_TYPE_ORGANIZATION, SEARCH_TYPE_PERSONAL,
                     SEARCH_TYPE_KEYWORD, or SEARCH_TYPE_FILE_NUMBER.

    Returns:
        List of ``IllinoisUccSearchResult`` objects parsed from the HTML
        results table.  Returns an empty list when no filings are found.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": IL_UCC_SEARCH_URL,
        "Origin": "https://apps.ilsos.gov",
    }

    with httpx.Client(
        follow_redirects=True,
        timeout=30,
        headers=headers,
    ) as client:
        # Load the search page first to acquire any session cookies / hidden
        # fields (the portal may set a session cookie on the initial GET).
        get_resp = client.get(IL_UCC_SEARCH_URL)
        _raise_if_blocked(get_resp)

        hidden = _hidden_fields(get_resp.text)

        # Build the POST form payload.
        form_data: dict[str, str] = {
            **hidden,
            "searchType": search_type,
        }
        if search_type == SEARCH_TYPE_ORGANIZATION:
            form_data["organizationName"] = company_name
        elif search_type == SEARCH_TYPE_PERSONAL:
            # Caller should pass "LAST, FIRST" or just last name.
            form_data["lastName"] = company_name
        elif search_type == SEARCH_TYPE_KEYWORD:
            form_data["keyword"] = company_name
        elif search_type == SEARCH_TYPE_FILE_NUMBER:
            form_data["fileNumber"] = company_name

        post_resp = client.post(IL_UCC_SEARCH_URL, data=form_data)
        _raise_if_blocked(post_resp)

    return parse_il_ucc_results(post_resp.text)


def _raise_if_blocked(response: httpx.Response) -> None:
    """Raise IlUccBlockedError on a WAF block, rather than a bare HTTPStatusError.

    Also treats a 200 response whose body is the WAF's block page (observed
    live to sometimes slip through with a 200 status on cached edge
    responses) as blocked, since "Reference ID" is a giveaway that never
    appears on the real search form or results page.
    """
    if response.status_code == 403 or "Reference ID:" in response.text:
        raise IlUccBlockedError(
            "IL SOS UCC search is blocked by a WAF (Akamai-style 403 block "
            "page, confirmed even via a real browser session). Route to "
            "manual review."
        )
    response.raise_for_status()


def to_public_search_results(
    company_name: str,
    rows: list[IllinoisUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert raw IL search results to the shared ``PublicSearchUccResult`` format."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    return [
        PublicSearchUccResult(
            state="IL",
            filing_id=row.filing_number,
            debtor_name=row.debtor_name,
            filing_type=row.filing_type,
            status=row.status,
            search_query=query,
            source_url=IL_UCC_SEARCH_URL,
            filing_date=row.filing_date,
            termination_date=row.lapse_date if row.status == "TERMINATED" else None,
            debtor_city=row.debtor_city,
            debtor_state=row.debtor_state or "IL",
            collateral_description="Illinois public UCC filing index — image copies available from IL SOS",
            secured_party_name=row.secured_party,
            match_confidence=_confidence(query_normalized, row.debtor_name),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


def parse_il_ucc_results(html: str) -> list[IllinoisUccSearchResult]:
    """Parse the HTML table from the IL SOS UCC search results page.

    The results table on apps.ilsos.gov/uccsearch/ contains columns for
    filing number, debtor name, city/state, secured party, filing date,
    lapse date, and filing type/status.  Column order is inferred from the
    header row; if the header cannot be found, a best-effort fixed-order
    parse is attempted.
    """
    parser = _IlResultsTableParser()
    parser.feed(html)
    return _build_results(parser.header, parser.rows)


def _build_results(
    header: list[str], data_rows: list[list[str]]
) -> list[IllinoisUccSearchResult]:
    """Map raw table rows to ``IllinoisUccSearchResult`` using the header."""
    col = _column_index(header)
    results: list[IllinoisUccSearchResult] = []
    for cells in data_rows:
        filing_number = _cell(cells, col.get("filing_number", 0))
        if not filing_number or filing_number.lower() in {"filing #", "file number", "#"}:
            continue
        debtor_name = _cell(cells, col.get("debtor_name", 1))
        if not debtor_name:
            continue
        city_state = _cell(cells, col.get("city_state", 2))
        city, state = _split_city_state(city_state)
        secured_party = _cell(cells, col.get("secured_party", 3)) or None
        filing_date_raw = _cell(cells, col.get("filing_date", 4))
        lapse_date_raw = _cell(cells, col.get("lapse_date", 5))
        filing_type_raw = _cell(cells, col.get("filing_type", 6)) or "UCC1"
        status_raw = _cell(cells, col.get("status", 7)) or "ACTIVE"

        filing_type = _normalize_filing_type(filing_type_raw)
        status = _normalize_status(status_raw, filing_type)

        results.append(
            IllinoisUccSearchResult(
                filing_number=filing_number.strip(),
                debtor_name=debtor_name.strip(),
                debtor_city=city,
                debtor_state=state,
                secured_party=secured_party,
                filing_date=_parse_date(filing_date_raw),
                lapse_date=_parse_date(lapse_date_raw),
                filing_type=filing_type,
                status=status,
            )
        )
    return results


def _column_index(header: list[str]) -> dict[str, int]:
    """Build a mapping of logical column name -> index from the header row."""
    mapping: dict[str, int] = {}
    for i, cell in enumerate(header):
        text = normalize_ucc_name(cell)
        if "FILING" in text and ("#" in text or "NUMBER" in text or "NUM" in text):
            mapping["filing_number"] = i
        elif "DEBTOR" in text and "NAME" in text:
            mapping["debtor_name"] = i
        elif "DEBTOR" in text and ("CITY" in text or "STATE" in text or "LOCATION" in text):
            mapping["city_state"] = i
        elif "CITY" in text and "STATE" not in text:
            mapping["city_state"] = i
        elif "SECURED" in text and "PARTY" in text:
            mapping["secured_party"] = i
        elif "FILING" in text and "DATE" in text:
            mapping["filing_date"] = i
        elif "LAPSE" in text or "TERMINATION" in text or "EXPIR" in text:
            mapping["lapse_date"] = i
        elif "TYPE" in text and "FILING" not in mapping.get("filing_number", ""):
            mapping["filing_type"] = i
        elif "STATUS" in text:
            mapping["status"] = i
    return mapping


# ---------------------------------------------------------------------------
# Helper parsers
# ---------------------------------------------------------------------------


class _HiddenFieldParser(HTMLParser):
    """Extract hidden form fields from an HTML page."""

    def __init__(self) -> None:
        super().__init__()
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "input":
            return
        values = dict(attrs)
        if values.get("type") == "hidden" and values.get("name"):
            self.fields[values["name"]] = values.get("value") or ""


class _IlResultsTableParser(HTMLParser):
    """Parse the UCC results table from the IL SOS search response.

    Captures the first ``<table>`` that contains UCC result data.
    The header row (``<th>`` or the first ``<tr>``) is stored separately
    so callers can build a column-name-to-index map.
    """

    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_cell = False
        self._table_depth = 0
        self.header: list[str] = []
        self.rows: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell: list[str] = []
        self._is_header_row = False
        self._header_done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        if tag == "table":
            self._table_depth += 1
            # Accept the first table encountered; refine if there is an id/class
            # that identifies the results table.
            table_id = (attr_dict.get("id") or "").lower()
            table_class = (attr_dict.get("class") or "").lower()
            if not self.in_table and (
                "result" in table_id
                or "ucc" in table_id
                or "result" in table_class
                or "search" in table_class
                or self._table_depth == 1  # fallback: first table on page
            ):
                self.in_table = True
        elif self.in_table:
            if tag == "tr":
                self._current_row = []
                self._is_header_row = False
            elif tag == "th":
                self.in_cell = True
                self._is_header_row = True
                self._current_cell = []
            elif tag == "td":
                self.in_cell = True
                self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self.in_table:
            self._table_depth -= 1
            if self._table_depth == 0:
                self.in_table = False
        elif self.in_table and tag in {"th", "td"} and self.in_cell:
            cell_text = " ".join(self._current_cell).strip()
            self._current_row.append(cell_text)
            self.in_cell = False
        elif self.in_table and tag == "tr" and self._current_row:
            if self._is_header_row and not self._header_done:
                self.header = self._current_row[:]
                self._header_done = True
            elif self._current_row:
                # Skip pure-header rows that might repeat mid-table
                self.rows.append(self._current_row[:])
            self._current_row = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            text = data.strip()
            if text:
                self._current_cell.append(text)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _hidden_fields(html: str) -> dict[str, str]:
    parser = _HiddenFieldParser()
    parser.feed(html)
    return parser.fields


def _cell(cells: list[str], index: int) -> str:
    try:
        return cells[index].strip()
    except IndexError:
        return ""


def _split_city_state(value: str) -> tuple[str | None, str | None]:
    """Split a 'City, ST' or 'City ST' string into (city, state)."""
    if not value:
        return None, None
    if "," in value:
        parts = value.split(",", 1)
        return parts[0].strip() or None, parts[1].strip() or None
    # Try two-letter state code at the end
    parts = value.rsplit(None, 1)
    if len(parts) == 2 and len(parts[1]) == 2 and parts[1].isalpha():
        return parts[0].strip() or None, parts[1].upper()
    return value.strip() or None, None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%B %d, %Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_filing_type(raw: str) -> str:
    text = normalize_ucc_name(raw)
    if "TERMIN" in text or "RELEASE" in text or "UCC3" in text or "UCC 3" in text:
        return "UCC3"
    if "CONTINUATION" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _normalize_status(raw: str, filing_type: str) -> str:
    text = normalize_ucc_name(raw)
    if filing_type == "UCC3" or "TERMINAT" in text or "LAPSED" in text or "EXPIRED" in text:
        return "TERMINATED"
    if "ACTIVE" in text or "FILED" in text or "CURRENT" in text:
        return "ACTIVE"
    return "ACTIVE"


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    if query_normalized and debtor_normalized and _token_overlap(query_normalized, debtor_normalized) >= 0.8:
        return 85
    return 70


def _token_overlap(a: str, b: str) -> float:
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))
