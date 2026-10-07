"""Targeted Arkansas UCC public-search connector.

Arkansas UCC filings are managed by the Secretary of State's Business and
Commercial Services (BCS) division at https://bcs.sos.arkansas.gov/search/ucc,
a React SPA on the same platform family as California's BizFile UCC search
(same "Execute search" aria-label, same disclaimer wording) -- but unlike
California, this one is NOT behind bot-management.

CONFIRMED WORKING (2026-07-02, live test) via Playwright. Real form flow:

    1. GET https://bcs.sos.arkansas.gov/search/ucc. The default view is a
       basic "Lien Number Search" box -- searching a company name here
       returns "No results found" because it's being interpreted as a lien
       number, not a name.
    2. Click the "Advanced" link/button to reveal Search Type radios:
       Lien Number Search / Debtor Name Search / Secured Party Name Search.
    3. Click "Debtor Name Search". A "Name Type" radio group appears:
       Individual Name / Organization Name (defaults to Individual, which
       shows First/Middle/Last Name fields instead).
    4. Click "Organization Name". This swaps in a single unlabeled text
       input (the second `input[type=text]` on the page, after the now-
       disabled basic search box) -- fill it with the debtor name.
    5. Click the "Search" button (role=button, name="Search", exact).
    6. Results render as a plain HTML <table class="div-table"> with 8
       columns: File Number, Debtor, Filing Type, Secured Party, Status,
       Filing Date, Lapse Date, Page Count. The Debtor and Secured Party
       cells include a " - CITY, STATE" suffix appended to the name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

AR_UCC_SEARCH_URL = "https://bcs.sos.arkansas.gov/search/ucc"

_ORG_NAME_INPUT_INDEX = 1  # second input[type=text] on the page


@dataclass(frozen=True)
class ArkansasUccSearchResult:
    filing_number: str
    debtor_name: str
    debtor_city: str | None
    debtor_state: str | None
    filing_type: str
    secured_party: str | None
    status: str
    filing_date: date | None
    lapse_date: date | None


def search_ar_ucc(company_name: str) -> list[ArkansasUccSearchResult]:
    """Search the AR BCS UCC portal for filings by organization debtor name.

    Requires Playwright + the chromium browser binary.
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
            page.goto(AR_UCC_SEARCH_URL, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(2000)

            page.get_by_text("Advanced", exact=True).click()
            page.wait_for_timeout(800)
            page.get_by_text("Debtor Name Search", exact=True).click()
            page.wait_for_timeout(400)
            page.get_by_text("Organization Name", exact=True).click()
            page.wait_for_timeout(400)

            org_field = page.locator("input[type=text]").nth(_ORG_NAME_INPUT_INDEX)
            if org_field.count() == 0:
                raise RuntimeError(
                    "AR UCC organization-name field not found; the "
                    "bcs.sos.arkansas.gov portal markup may have changed."
                )
            org_field.click()
            org_field.type(company_name, delay=30)
            page.wait_for_timeout(300)

            page.get_by_role("button", name="Search", exact=True).click()
            page.wait_for_timeout(2500)

            html = page.content()
        finally:
            browser.close()

    return parse_ar_ucc_results(html)


def to_public_search_results(
    company_name: str,
    rows: list[ArkansasUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert raw AR search results to the shared PublicSearchUccResult shape."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    return [
        PublicSearchUccResult(
            state="AR",
            filing_id=row.filing_number,
            debtor_name=row.debtor_name,
            filing_type=_canonical_filing_type(row.filing_type),
            status=_canonical_status(row.status),
            search_query=query,
            source_url=AR_UCC_SEARCH_URL,
            secured_party_name=row.secured_party,
            filing_date=row.filing_date,
            termination_date=row.lapse_date if _canonical_status(row.status) == "TERMINATED" else None,
            debtor_city=row.debtor_city,
            debtor_state=row.debtor_state or "AR",
            collateral_description=None,
            match_confidence=_confidence(query_normalized, row.debtor_name),
        )
        for row in rows
    ]


def parse_ar_ucc_results(html: str) -> list[ArkansasUccSearchResult]:
    """Parse the AR UCC results table (class="div-table").

    Live-confirmed columns: File Number, Debtor, Filing Type, Secured
    Party, Status, Filing Date, Lapse Date, Page Count. Debtor/Secured
    Party cells include a " - CITY, STATE" suffix that must be split off.
    """
    parser = _ResultsTableParser()
    parser.feed(html)
    results: list[ArkansasUccSearchResult] = []
    for cells in parser.rows:
        if len(cells) < 7:
            continue
        filing_number = cells[0].strip()
        if not filing_number or filing_number.lower() in {"file number", "filing number"}:
            continue
        debtor_raw = cells[1].strip()
        debtor_name, debtor_city, debtor_state = _split_name_location(debtor_raw)
        filing_type = cells[2].strip()
        secured_raw = cells[3].strip()
        secured_party, _, _ = _split_name_location(secured_raw)
        status = cells[4].strip()
        filing_date = _parse_date(cells[5])
        lapse_date = _parse_date(cells[6])

        results.append(
            ArkansasUccSearchResult(
                filing_number=filing_number,
                debtor_name=debtor_name,
                debtor_city=debtor_city,
                debtor_state=debtor_state,
                filing_type=filing_type,
                secured_party=secured_party or None,
                status=status,
                filing_date=filing_date,
                lapse_date=lapse_date,
            )
        )
    return results


def _split_name_location(raw: str) -> tuple[str, str | None, str | None]:
    """Split "NAME - CITY, STATE" into (name, city, state)."""
    if " - " not in raw:
        return raw, None, None
    name, _, location = raw.partition(" - ")
    if "," in location:
        city, _, state = location.partition(",")
        return name.strip(), city.strip() or None, state.strip() or None
    return name.strip(), None, location.strip() or None


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    text = value.strip().split(" ")[0]
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _canonical_filing_type(raw: str) -> str:
    text = raw.upper()
    if "TERMIN" in text or "RELEASE" in text:
        return "UCC3"
    if "CONTINUATION" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _canonical_status(raw: str) -> str:
    text = raw.upper()
    if "ACTIVE" in text:
        return "ACTIVE"
    if any(word in text for word in ("TERMINAT", "RELEASE", "LAPSED", "INACTIVE")):
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
    """Extract rows from the AR UCC results table (class="div-table")."""

    def __init__(self) -> None:
        super().__init__()
        self._in_table = False
        self._depth = 0
        self._in_cell = False
        self._current_cell: list[str] = []
        self._current_row: list[str] = []
        self.rows: list[list[str]] = []
        self._found = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "table":
            self._depth += 1
            if not self._found and "div-table" in values.get("class", ""):
                self._in_table = True
                self._found = True
        elif self._in_table and tag == "tr":
            self._current_row = []
        elif self._in_table and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self._depth -= 1
            if self._in_table and self._depth == 0:
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
