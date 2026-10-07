"""Targeted South Carolina UCC public-search connector.

SC UCC filings are managed by the Secretary of State through a Tyler
Technologies-hosted ASP.NET portal at ucconline.sc.gov (the same platform
used by Maryland). There is no free bulk download -- bulk data costs
~$12,000/year via a paid subscriber agreement.

CONFIRMED WORKING (2026-07-03, live test): unlike Maryland, SC's free
public Name Search does NOT require a CAPTCHA. It is a two-step flow:

1. GET  MainMenu.aspx -> click "File / Search Now"
   (id=ctl00_MainContentPlaceHolder_NonSubscriberButton)
2. Click "Name Search" -> UCCPartyNameSearchMainPage.aspx
   Fill the party-name field
   (id=ctl00_MainContentPlaceHolder_NameSearchControl1_PartyNameTextBox)
   Submit id=ctl00_MainContentPlaceHolder_ContinueButton
3. The server does NOT return filings directly -- it returns a
   *name-disambiguation* page (UCCPartyNameSelectionPage.aspx) listing every
   distinct party name that matched, each with a checkbox
   (id contains "PartyNameCheckBox"). Check every matching box and submit
   id=ctl00_MainContentPlaceHolder_UCCSearchResultsByPartyNameControl1_ContinueButton.
4. This lands on UCCSearchResultsRetrievalPage.aspx with a Telerik RadGrid
   (id=..._UCCSearchResultsByFilingNumberControl1_RadGrid1_ctl00) containing
   the real filing rows. Live-confirmed columns (4, not the 7 assumed by an
   earlier version of this connector): Filing Number, Filing Type,
   Filing Date, Lapse Date. There is no separate debtor/secured-party/status
   column in this grid -- status is derived from the lapse date and filing
   type below.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

SC_UCC_MAIN_URL = "https://ucconline.sc.gov/UCCFiling/MainMenu.aspx"
SC_UCC_SEARCH_URL = SC_UCC_MAIN_URL

_NON_SUBSCRIBER_BUTTON_SELECTOR = "#ctl00_MainContentPlaceHolder_NonSubscriberButton"
_NAME_SEARCH_LINK_TEXT = "text=Name Search"
_PARTY_NAME_SELECTOR = "#ctl00_MainContentPlaceHolder_NameSearchControl1_PartyNameTextBox"
_CONTINUE_BUTTON_SELECTOR = "#ctl00_MainContentPlaceHolder_ContinueButton"
_NAME_CHECKBOX_SELECTOR = "input[id*='PartyNameCheckBox']"
_SELECTION_CONTINUE_SELECTOR = (
    "#ctl00_MainContentPlaceHolder_UCCSearchResultsByPartyNameControl1_ContinueButton"
)


@dataclass(frozen=True)
class ScUccSearchResult:
    """A single row from the SC UCC filing-results grid."""

    filing_number: str
    filing_type: str
    filing_date: date | None
    lapse_date: date | None


def search_sc_ucc(company_name: str) -> list[ScUccSearchResult]:
    """Search the SC UCC portal for filings matching *company_name*.

    Requires Playwright + the chromium browser binary. Raises on failure
    (form field missing, no matching names, navigation error) rather than
    silently returning an empty list, so callers can distinguish "genuinely
    no filings" from "the search broke."
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
            page.goto(SC_UCC_MAIN_URL, wait_until="domcontentloaded")
            page.click(_NON_SUBSCRIBER_BUTTON_SELECTOR)
            page.wait_for_load_state("domcontentloaded")
            page.click(_NAME_SEARCH_LINK_TEXT)
            page.wait_for_load_state("domcontentloaded")

            party_field = page.locator(_PARTY_NAME_SELECTOR)
            if party_field.count() == 0:
                raise RuntimeError(
                    "SC UCC search field not found; the ucconline.sc.gov portal "
                    "markup may have changed."
                )
            party_field.fill(company_name)
            page.click(_CONTINUE_BUTTON_SELECTOR)
            page.wait_for_load_state("load", timeout=20_000)
            page.wait_for_timeout(1000)

            checkboxes = page.locator(_NAME_CHECKBOX_SELECTOR)
            match_count = checkboxes.count()
            if match_count == 0:
                # Genuinely no matching party names -- not a connector failure.
                return []
            for i in range(match_count):
                checkboxes.nth(i).check()
            page.click(_SELECTION_CONTINUE_SELECTOR)
            page.wait_for_load_state("load", timeout=20_000)
            page.wait_for_timeout(1000)

            html = page.content()
        finally:
            browser.close()

    return parse_sc_ucc_results(html)


def to_public_search_results(
    company_name: str, rows: list[ScUccSearchResult]
) -> list[PublicSearchUccResult]:
    """Convert raw SC search rows into the shared PublicSearchUccResult format."""
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    return [
        PublicSearchUccResult(
            state="SC",
            filing_id=row.filing_number,
            debtor_name=query,
            filing_type=_canonical_filing_type(row.filing_type),
            status=_canonical_status(row.filing_type, row.lapse_date),
            search_query=query,
            source_url=SC_UCC_SEARCH_URL,
            secured_party_name=None,
            filing_date=row.filing_date,
            termination_date=row.lapse_date
            if _canonical_filing_type(row.filing_type) == "UCC3"
            else None,
            debtor_state="SC",
            collateral_description=None,
            match_confidence=_confidence(query_normalized),
        )
        for row in rows
    ]


def parse_sc_ucc_results(html: str) -> list[ScUccSearchResult]:
    """Parse the SC UCC filing-results grid.

    Live-confirmed column layout (2026-07-03): the grid has two leading
    checkbox columns (select-all header cell, per-row retrieval checkbox)
    before the real data starts, e.g.:
        ['&nbsp;', '', 'Filing Number', 'Filing Type', 'Filing Date', 'Lapse Date']
        ['',       '', '230612-1919281', 'UCC-1 Financing Statement', '6/12/2023 ...', '6/12/2028']
    Data columns are therefore at indices 2-5, not 0-3.
    """
    parser = _ResultsTableParser()
    parser.feed(html)
    rows: list[ScUccSearchResult] = []
    for cells in parser.rows:
        if len(cells) < 6:
            continue
        filing_number = cells[2].strip()
        if not filing_number or filing_number.lower() in {
            "filing number",
            "filing #",
            "file number",
        }:
            continue
        rows.append(
            ScUccSearchResult(
                filing_number=filing_number,
                filing_type=cells[3].strip(),
                filing_date=_parse_date(cells[4]),
                lapse_date=_parse_date(cells[5]),
            )
        )
    return rows


def _confidence(query_normalized: str) -> int:
    return 90 if query_normalized else 70


def _parse_date(value: str) -> date | None:
    text = value.strip().split(" ")[0] if value else ""
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
    if "CONTINUATION" in text or "CONT" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _canonical_status(filing_type_raw: str, lapse_date: date | None) -> str:
    filing_type = _canonical_filing_type(filing_type_raw)
    if filing_type == "UCC3":
        return "TERMINATED"
    if lapse_date is not None and lapse_date < date.today():
        return "TERMINATED"
    return "ACTIVE"


class _ResultsTableParser(HTMLParser):
    """Extract rows from the SC filing-results Telerik RadGrid."""

    def __init__(self) -> None:
        super().__init__()
        self.in_results_table: bool = False
        self.in_cell: bool = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []
        self._depth: int = 0
        self._table_depth: int = 0
        self._found = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "table":
            self._depth += 1
            table_id = values.get("id", "").lower()
            table_class = values.get("class", "").lower()
            if not self._found and (
                "rgmastertable" in table_class
                or "resultsgrid" in table_id
                or "gridview" in table_id
                or "radgrid" in table_id
            ):
                self.in_results_table = True
                self._table_depth = self._depth
                self._found = True
        elif self.in_results_table and tag == "tr":
            self.current_row = []
        elif self.in_results_table and tag in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            if self.in_results_table and self._depth == self._table_depth:
                self.in_results_table = False
            self._depth -= 1
        elif self.in_results_table and tag in {"td", "th"} and self.in_cell:
            self.current_row.append(" ".join(self.current_cell).strip())
            self.in_cell = False
        elif self.in_results_table and tag == "tr" and self.current_row:
            self.rows.append(self.current_row)
            self.current_row = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if self.in_cell and text:
            self.current_cell.append(text)
