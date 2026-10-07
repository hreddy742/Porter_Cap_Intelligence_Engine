"""Minnesota UCC targeted-search connector.

MN UCC data availability summary
---------------------------------
The Minnesota MBLS portal (mblsportal.sos.mn.gov) exposes three search tabs:

  1. File Number  — free, no account required; returns one filing by exact
                    file number.  Useful only when a file number is already
                    known (e.g. from a lender relationship).
  2. UCC Debtor Name — requires a paid MBLS online account **and** a lookup
                        subscription ($0.40 per name / $10 per 25 lookups).
  3. Tax Lien Debtor Name — same paywall as (2).

Bulk data is available from MN SOS for $9 600 (initial) + $2 400/quarter
with a signed license agreement.  Contact: ucc.dept@state.mn.us.

Because no free debtor-name endpoint exists this connector implements the
targeted_search acquisition method with two public functions:

  search_mn_ucc_by_file_number(file_number)
      Free.  Returns zero or one PublicSearchUccResult.

  search_mn_ucc(company_name)
      Requires ``MN_UCC_USERNAME`` and ``MN_UCC_PASSWORD`` environment
      variables (MBLS credentials).  Raises ``MnUccAuthRequired`` when
      credentials are absent.  Raises ``MnUccPaywallError`` if the portal
      returns a paywall / login-required page instead of results.

Usage (refresh script)
----------------------
  python scripts/refresh_mn_ucc.py "ACME CORP"

Environment variables
---------------------
  MN_UCC_USERNAME  — MBLS portal username (email)
  MN_UCC_PASSWORD  — MBLS portal password
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from typing import TYPE_CHECKING

import httpx

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MN_UCC_PORTAL_BASE = "https://mblsportal.sos.mn.gov"
MN_UCC_SEARCH_URL = f"{MN_UCC_PORTAL_BASE}/Secured/SearchUCC"
MN_UCC_FILE_NUMBER_SEARCH_URL = f"{MN_UCC_PORTAL_BASE}/Secured/FileNumberSearch"
MN_UCC_LOGIN_URL = f"{MN_UCC_PORTAL_BASE}/Login"
MN_UCC_SOURCE_URL = MN_UCC_SEARCH_URL

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": MN_UCC_PORTAL_BASE,
    "Accept-Language": "en-US,en;q=0.9",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MnUccAuthRequired(RuntimeError):
    """Raised when MBLS credentials are not configured."""


class MnUccPaywallError(RuntimeError):
    """Raised when the portal returns a login/paywall page instead of results."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MnUccSearchResult:
    filing_number: str
    debtor_name: str
    debtor_address: str | None
    debtor_city: str | None
    debtor_state: str | None
    debtor_zip: str | None
    secured_party_name: str | None
    filing_type: str
    filing_date: date | None
    lapse_date: date | None
    status: str
    collateral_description: str | None


# ---------------------------------------------------------------------------
# Public API — file-number lookup (free)
# ---------------------------------------------------------------------------


def search_mn_ucc_by_file_number(
    file_number: str,
) -> list[PublicSearchUccResult]:
    """Look up a single MN UCC filing by exact file number (free, no auth).

    Returns an empty list when the file number is not found.

    PARTIALLY VERIFIED (2026-07-03): fixed the POST target (real form action
    is /Secured/FileNumberSearch, not the search page itself) and the real
    field name (fileNumber, lowercase -- not FileNumber). Confirmed the
    request round-trips without error against a live session, but the
    resulting redirect URL includes "IncludeUccFilings=False", suggesting
    an additional checkbox field is still required to actually scope the
    search to UCC records rather than tax liens -- not yet found. This
    function is NOT part of the wired SUPPORTED_STATES search path (which
    uses search_mn_ucc, the debtor-name search, confirmed correctly
    auth-gated); treat this helper as unverified until that field is found.
    """
    with httpx.Client(
        follow_redirects=True,
        timeout=30,
        headers=_HEADERS,
    ) as client:
        landing = client.get(MN_UCC_SEARCH_URL)
        landing.raise_for_status()
        form_data = _extract_hidden_fields(landing.text)
        form_data.update(
            {
                "fileNumber": file_number.strip(),
                "hdnProductType": "UCC",
            }
        )
        response = client.post(MN_UCC_FILE_NUMBER_SEARCH_URL, data=form_data)
        response.raise_for_status()

    rows = _parse_mn_results(response.text)
    return _to_public_results(
        search_query=file_number,
        rows=rows,
        acquisition_method="targeted_search",
    )


# ---------------------------------------------------------------------------
# Public API — debtor name search (requires paid MBLS account)
# ---------------------------------------------------------------------------


def search_mn_ucc(company_name: str) -> list[PublicSearchUccResult]:
    """Search MN UCC filings by debtor organization name.

    Requires the ``MN_UCC_USERNAME`` and ``MN_UCC_PASSWORD`` environment
    variables to be set with valid MBLS portal credentials.

    Raises
    ------
    MnUccAuthRequired
        When the environment variables are missing.
    MnUccPaywallError
        When the portal redirects to a login page (e.g. subscription lapsed).
    """
    username = os.environ.get("MN_UCC_USERNAME", "").strip()
    password = os.environ.get("MN_UCC_PASSWORD", "").strip()
    if not username or not password:
        raise MnUccAuthRequired(
            "MN UCC debtor-name search requires a paid MBLS account. "
            "Set MN_UCC_USERNAME and MN_UCC_PASSWORD environment variables. "
            "Create an account at https://mblsportal.sos.mn.gov and purchase "
            "a UCC lookup subscription ($10 per 25 searches). "
            "Contact ucc.dept@state.mn.us or 651-296-2803 for details."
        )

    with httpx.Client(
        follow_redirects=True,
        timeout=30,
        headers=_HEADERS,
    ) as client:
        # Step 1 — authenticate
        login_page = client.get(MN_UCC_LOGIN_URL)
        login_page.raise_for_status()
        login_data = _extract_hidden_fields(login_page.text)
        login_data.update(
            {
                "Username": username,
                "Password": password,
            }
        )
        login_resp = client.post(MN_UCC_LOGIN_URL, data=login_data)
        login_resp.raise_for_status()

        # Verify we are authenticated (portal redirects away from login on success)
        if "login" in login_resp.url.path.lower() or _is_login_page(login_resp.text):
            raise MnUccPaywallError(
                "MN MBLS login failed — check MN_UCC_USERNAME / MN_UCC_PASSWORD."
            )

        # Step 2 — load the UCC search page (now authenticated)
        search_page = client.get(MN_UCC_SEARCH_URL)
        search_page.raise_for_status()

        if _is_login_page(search_page.text):
            raise MnUccPaywallError(
                "MN MBLS portal requires a UCC lookup subscription. "
                "Purchase one at https://mblsportal.sos.mn.gov."
            )

        form_data = _extract_hidden_fields(search_page.text)
        form_data.update(
            {
                "SearchType": "UCCDebtorName",
                "OrganizationName": company_name.strip(),
            }
        )

        results_page = client.post(MN_UCC_SEARCH_URL, data=form_data)
        results_page.raise_for_status()

        if _is_login_page(results_page.text):
            raise MnUccPaywallError(
                "MN MBLS portal returned a login page — subscription may have lapsed."
            )

    rows = _parse_mn_results(results_page.text)
    return _to_public_results(
        search_query=company_name,
        rows=rows,
        acquisition_method="targeted_search",
    )


# ---------------------------------------------------------------------------
# Result conversion
# ---------------------------------------------------------------------------


def to_public_search_results(
    company_name: str,
    rows: list[MnUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert parsed MN search rows to canonical PublicSearchUccResult objects."""
    return _to_public_results(
        search_query=company_name,
        rows=rows,
        acquisition_method="targeted_search",
    )


def _to_public_results(
    *,
    search_query: str,
    rows: list[MnUccSearchResult],
    acquisition_method: str,
) -> list[PublicSearchUccResult]:
    query_normalized = normalize_ucc_name(search_query)
    out: list[PublicSearchUccResult] = []
    for row in rows:
        out.append(
            PublicSearchUccResult(
                state="MN",
                filing_id=row.filing_number,
                debtor_name=row.debtor_name,
                filing_type=row.filing_type,
                status=row.status,
                search_query=search_query,
                source_url=MN_UCC_SOURCE_URL,
                secured_party_name=row.secured_party_name,
                filing_date=row.filing_date,
                termination_date=row.lapse_date,
                collateral_description=row.collateral_description,
                debtor_address=row.debtor_address,
                debtor_city=row.debtor_city,
                debtor_state=row.debtor_state,
                debtor_zip=row.debtor_zip,
                match_confidence=_confidence(query_normalized, row.debtor_name),
            )
        )
    return out


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


def _parse_mn_results(html: str) -> list[MnUccSearchResult]:
    """Parse the MBLS portal results page into MnUccSearchResult objects.

    The MBLS portal renders results in an HTML table.  The column order
    observed from the live portal is:

        Filing Number | Debtor Name | Debtor Address | Secured Party |
        Filing Type | Filing Date | Lapse Date | Status | Collateral

    If the portal changes its layout the parser will return an empty list
    rather than crashing.
    """
    parser = _MnResultsParser()
    parser.feed(html)
    results: list[MnUccSearchResult] = []
    for cells in parser.rows:
        # Skip header rows and short rows
        if len(cells) < 6:
            continue
        # Detect header row (first cell contains 'filing' or 'number')
        first_lower = cells[0].lower()
        if "filing" in first_lower or "number" in first_lower or "debtor" in first_lower:
            continue

        filing_number = cells[0].strip()
        if not filing_number:
            continue

        debtor_name = cells[1].strip() if len(cells) > 1 else ""
        debtor_raw_address = cells[2].strip() if len(cells) > 2 else ""
        secured_party = cells[3].strip() if len(cells) > 3 else None
        filing_type_raw = cells[4].strip() if len(cells) > 4 else "UCC1"
        filing_date_raw = cells[5].strip() if len(cells) > 5 else ""
        lapse_date_raw = cells[6].strip() if len(cells) > 6 else ""
        status_raw = cells[7].strip() if len(cells) > 7 else "ACTIVE"
        collateral_raw = cells[8].strip() if len(cells) > 8 else None

        # Parse address — the portal often puts "City, ST ZIP" in one cell
        city, state, zip_code = _parse_address_cell(debtor_raw_address)

        results.append(
            MnUccSearchResult(
                filing_number=filing_number,
                debtor_name=debtor_name,
                debtor_address=debtor_raw_address or None,
                debtor_city=city,
                debtor_state=state,
                debtor_zip=zip_code,
                secured_party_name=secured_party or None,
                filing_type=_normalise_filing_type(filing_type_raw),
                filing_date=_parse_date(filing_date_raw),
                lapse_date=_parse_date(lapse_date_raw),
                status=_normalise_status(status_raw, filing_type_raw),
                collateral_description=collateral_raw or None,
            )
        )
    return results


def _parse_address_cell(raw: str) -> tuple[str | None, str | None, str | None]:
    """Attempt to extract city, state, zip from a combined address string.

    Handles formats such as:
      "Minneapolis, MN 55401"
      "MINNEAPOLIS MN 55401"
      "123 Main St, Minneapolis, MN 55401"
    Returns (city, state, zip) — any or all may be None.
    """
    if not raw:
        return None, None, None
    parts = [p.strip() for p in raw.replace(",", " ").split()]
    # Heuristic: look for a 2-letter uppercase token followed by a zip-like token
    for i, token in enumerate(parts):
        if len(token) == 2 and token.isalpha() and token.isupper():
            state = token
            zip_code = parts[i + 1] if i + 1 < len(parts) and _looks_like_zip(parts[i + 1]) else None
            city = parts[i - 1] if i > 0 else None
            return city, state, zip_code
    return None, None, None


def _looks_like_zip(s: str) -> bool:
    return len(s) in {5, 10} and s[:5].isdigit()


def _normalise_filing_type(raw: str) -> str:
    upper = raw.upper()
    if "TERMINAT" in upper or "RELEASE" in upper:
        return "UCC3"
    if "AMENDMENT" in upper or "AMEND" in upper:
        return "AMENDMENT"
    if "CONTINUATION" in upper:
        return "CONTINUATION"
    return "UCC1"


def _normalise_status(raw: str, filing_type_raw: str) -> str:
    upper = raw.upper()
    if "TERMINAT" in upper or "LAPSED" in upper or "RELEASE" in upper:
        return "TERMINATED"
    ft_upper = filing_type_raw.upper()
    if "TERMINAT" in ft_upper or "RELEASE" in ft_upper:
        return "TERMINATED"
    return "ACTIVE"


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _confidence(query_normalized: str, debtor_name: str) -> int:
    if not query_normalized:
        return 50
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    # Check if all query tokens appear in debtor
    q_tokens = set(query_normalized.split())
    d_tokens = set(debtor_normalized.split())
    if q_tokens and q_tokens.issubset(d_tokens):
        return 80
    return 60


def _is_login_page(html: str) -> bool:
    lower = html.lower()
    return (
        "id=\"username\"" in lower
        or "id=\"password\"" in lower
        or "name=\"password\"" in lower
        or "please log in" in lower
        or "sign in to continue" in lower
        or "login required" in lower
    )


def _extract_hidden_fields(html: str) -> dict[str, str]:
    parser = _HiddenFieldParser()
    parser.feed(html)
    return parser.fields


# ---------------------------------------------------------------------------
# HTML parser helpers
# ---------------------------------------------------------------------------


class _HiddenFieldParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "input":
            return
        values = dict(attrs)
        if values.get("type") == "hidden" and values.get("name"):
            self.fields[values["name"]] = values.get("value") or ""


class _MnResultsParser(HTMLParser):
    """Parse an MBLS results page — extracts rows from the first data table."""

    def __init__(self) -> None:
        super().__init__()
        self._in_table = False
        self._table_depth = 0
        self._in_cell = False
        self._current_cell: list[str] = []
        self._current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "table":
            self._table_depth += 1
            # Capture the first table that looks like a results grid
            if not self._in_table:
                table_id = values.get("id", "")
                table_class = values.get("class", "")
                if (
                    "result" in table_id.lower()
                    or "result" in table_class.lower()
                    or "grid" in table_id.lower()
                    or "grid" in table_class.lower()
                    or self._table_depth == 1  # fallback: first top-level table
                ):
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
