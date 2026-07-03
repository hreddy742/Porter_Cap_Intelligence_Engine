"""Targeted Maryland UCC public-search connector.

Maryland UCC is managed via egov.maryland.gov/SDAT/UCCFiling/ (Tyler
Technologies / NICUSA), an ASP.NET WebForms application. There is no bulk
download or open dataset.

CONFIRMED BLOCKED (2026-07-03, live test): the free public Name Search
requires solving a CAPTCHA before the server returns results -- confirmed
via a real Playwright/Chromium session that filled the real search field
and submitted the form; the response was "Invalid Captcha entry, please
try again." This is independent of form-field correctness (verified real
navigation flow and field name below) and cannot be bypassed without a
CAPTCHA-solving integration, which is out of scope for this connector.
search_md_ucc() raises MdUccCaptchaRequiredError so callers can route to
manual review instead of silently returning an empty result set.

Real navigation flow (captured 2026-07-03 via live Playwright session):
    1. GET  UCCMainPage.aspx
    2. Click "File / Search Now" (id=MainContentPlaceHolder_NonSubscriberButton)
       -> redirects to MainMenu.aspx
    3. Click "Name Search" link -> NewSearchByPartyName.aspx
       -> redirects to UCCPartyNameSearchMainPage.aspx
    4. The visible search field is a SINGLE unified party-name box:
       id=MainContentPlaceHolder_NameSearchControl1_PartyNameTextBox
       (accepts "Last, First" or an organization name). The separate
       OrganizationTextBox/IndividualNameTextBox fields referenced by an
       earlier version of this connector exist in the DOM but are hidden
       and not the active input on the current portal layout.
    5. Submit id=MainContentPlaceHolder_ContinueButton -> CAPTCHA required.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

MD_UCC_MAIN_URL = "https://egov.maryland.gov/SDAT/UCCFiling/UCCMainPage.aspx"
MD_UCC_SEARCH_URL = "https://egov.maryland.gov/SDAT/UCCFiling/UCCPartyNameSearchMainPage.aspx"

_PARTY_NAME_SELECTOR = "#MainContentPlaceHolder_NameSearchControl1_PartyNameTextBox"
_CONTINUE_BUTTON_SELECTOR = "#MainContentPlaceHolder_ContinueButton"
_NON_SUBSCRIBER_BUTTON_SELECTOR = "#MainContentPlaceHolder_NonSubscriberButton"
_NAME_SEARCH_LINK_TEXT = "text=Name Search"


class MdUccCaptchaRequiredError(RuntimeError):
    """Raised when the Maryland UCC search portal demands a CAPTCHA solve."""


@dataclass(frozen=True)
class MarylandUccSearchResult:
    """One row returned by the Maryland UCC debtor-name search."""

    filing_number: str
    debtor_name: str
    secured_party: str | None
    filing_type: str
    status: str
    filing_date: date | None
    lapse_date: date | None


def search_md_ucc(company_name: str) -> list[MarylandUccSearchResult]:
    """Search the Maryland SDAT UCC portal for filings by debtor name.

    Requires Playwright + the chromium browser binary. Raises
    ``MdUccCaptchaRequiredError`` because the live portal currently demands a
    CAPTCHA solve before returning results -- confirmed 2026-07-03.
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
            page.goto(MD_UCC_MAIN_URL, wait_until="domcontentloaded")
            page.click(_NON_SUBSCRIBER_BUTTON_SELECTOR)
            page.wait_for_load_state("domcontentloaded")
            page.click(_NAME_SEARCH_LINK_TEXT)
            page.wait_for_load_state("domcontentloaded")

            party_field = page.locator(_PARTY_NAME_SELECTOR)
            if party_field.count() == 0:
                raise RuntimeError(
                    "MD UCC search field not found; the egov.maryland.gov portal "
                    "markup may have changed."
                )
            party_field.fill(company_name)
            page.click(_CONTINUE_BUTTON_SELECTOR)
            page.wait_for_load_state("load", timeout=20_000)
            page.wait_for_timeout(1500)

            body_text = page.inner_text("body")
            if "captcha" in body_text.lower():
                raise MdUccCaptchaRequiredError(
                    "MD UCC search requires solving a CAPTCHA before returning "
                    "results. Route to manual review."
                )

            html = page.content()
        finally:
            browser.close()

    return parse_md_ucc_results(html)


def to_public_search_results(
    company_name: str,
    rows: list[MarylandUccSearchResult],
) -> list[PublicSearchUccResult]:
    """Convert raw Maryland search results to the shared ``PublicSearchUccResult`` DTO."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    return [
        PublicSearchUccResult(
            state="MD",
            filing_id=row.filing_number,
            debtor_name=row.debtor_name,
            filing_type=_filing_type(row.filing_type),
            status=_status(row.status, row.filing_type),
            search_query=query,
            source_url=MD_UCC_SEARCH_URL,
            secured_party_name=row.secured_party,
            filing_date=row.filing_date,
            termination_date=row.lapse_date,
            debtor_state="MD",
            collateral_description="Maryland public UCC debtor-name search result",
            match_confidence=_confidence(query_normalized, row.debtor_name),
        )
        for row in rows
    ]


def parse_md_ucc_results(html: str) -> list[MarylandUccSearchResult]:
    """Parse the results table from the Maryland UCC search response page."""
    parser = _ResultsTableParser()
    parser.feed(html)
    results: list[MarylandUccSearchResult] = []
    for cells in parser.rows:
        if len(cells) < 5:
            continue
        if cells[0].lower() in {"filing number", "filing #", "filenumber", "number"}:
            continue
        filing_number = cells[0].strip()
        if not filing_number:
            continue
        debtor_name = cells[1].strip() if len(cells) > 1 else ""
        secured_party = cells[2].strip() or None if len(cells) > 2 else None
        filing_type_raw = cells[3].strip() if len(cells) > 3 else ""
        status_raw = cells[4].strip() if len(cells) > 4 else ""
        filing_date = _parse_date(cells[5]) if len(cells) > 5 else None
        lapse_date = _parse_date(cells[6]) if len(cells) > 6 else None

        if not debtor_name:
            continue

        results.append(
            MarylandUccSearchResult(
                filing_number=filing_number,
                debtor_name=debtor_name,
                secured_party=secured_party,
                filing_type=filing_type_raw,
                status=status_raw,
                filing_date=filing_date,
                lapse_date=lapse_date,
            )
        )
    return results


def _filing_type(value: str) -> str:
    text = normalize_ucc_name(value)
    if "TERMIN" in text or "RELEASE" in text:
        return "UCC3"
    if "AMEND" in text:
        return "AMENDMENT"
    if "CONTINU" in text:
        return "CONTINUATION"
    return "UCC1"


def _status(value: str, filing_type_raw: str) -> str:
    text = normalize_ucc_name(value)
    filing_type = _filing_type(filing_type_raw)
    if filing_type == "UCC3" or "TERMIN" in text or "LAPSED" in text or "RELEASED" in text:
        return "TERMINATED"
    if "ACTIVE" in text or "FILED" in text:
        return "ACTIVE"
    if filing_type == "AMENDMENT":
        return "AMENDED"
    return value.upper() if value else "ACTIVE"


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    return 70


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


class _ResultsTableParser(HTMLParser):
    """Extract rows from the first results table on the Maryland search page."""

    def __init__(self) -> None:
        super().__init__()
        self.in_results_table = False
        self.depth = 0
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []
        self._found = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "table":
            if not self._found:
                table_id = values.get("id", "").lower()
                table_class = values.get("class", "").lower()
                if (
                    "gridview" in table_id
                    or "results" in table_id
                    or "grid" in table_class
                    or "results" in table_class
                ):
                    self.in_results_table = True
                    self._found = True
                    self.depth = 1
                    return
            if self.in_results_table:
                self.depth += 1
        elif self.in_results_table:
            if tag == "tr":
                self.current_row = []
            elif tag in {"td", "th"}:
                self.in_cell = True
                self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self.in_results_table:
            self.depth -= 1
            if self.depth == 0:
                self.in_results_table = False
        elif self.in_results_table:
            if tag in {"td", "th"} and self.in_cell:
                self.current_row.append(" ".join(self.current_cell).strip())
                self.in_cell = False
                self.current_cell = []
            elif tag == "tr" and self.current_row:
                self.rows.append(self.current_row)
                self.current_row = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            text = data.strip()
            if text:
                self.current_cell.append(text)
