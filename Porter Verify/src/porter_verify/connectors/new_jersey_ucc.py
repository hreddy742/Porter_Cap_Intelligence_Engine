"""Targeted New Jersey UCC public-search connector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser

import httpx

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

NJ_UCC_SEARCH_URL = "https://www.njportal.com/UCC/Search/NonCertifiedSearch.aspx"
NJ_UCC_START_CONTINUE_FIELD = (
    "ctl00$mainContent$DebtorSearch1$Wizard1$StartNavigationTemplateContainerID$btnContinue"
)
NJ_UCC_STEP_SEARCH_FIELD = (
    "ctl00$mainContent$DebtorSearch1$Wizard1$StepNavigationTemplateContainerID$btnContinue"
)


@dataclass(frozen=True)
class NewJerseyUccSearchResult:
    organization_name: str
    city: str | None
    filing_number: str
    status: str
    filing_date: date | None
    page_count: int | None


def search_new_jersey_ucc(
    company_name: str, *, include_lapsed: bool = False
) -> list[NewJerseyUccSearchResult]:
    with httpx.Client(
        follow_redirects=True,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0", "Referer": NJ_UCC_SEARCH_URL},
    ) as client:
        first = client.get(NJ_UCC_SEARCH_URL)
        first.raise_for_status()
        data = _hidden_fields(first.text)
        data.update(
            {
                "ctl00$mainContent$DebtorSearch1$Wizard1$radioSwitchOrgPerson": "Organization",
                "ctl00$mainContent$DebtorSearch1$Wizard1$radioOutputList": "StatusReport",
                NJ_UCC_START_CONTINUE_FIELD: "Continue",
            }
        )
        second = client.post(NJ_UCC_SEARCH_URL, data=data)
        second.raise_for_status()
        data = _hidden_fields(second.text)
        if include_lapsed:
            data["ctl00$mainContent$DebtorSearch1$Wizard1$cbIncludeLapsedOrg"] = "on"
        data.update(
            {
                "ctl00$mainContent$DebtorSearch1$Wizard1$txtOrganizationName": company_name,
                "ctl00$mainContent$DebtorSearch1$Wizard1$txtOrgCity": "",
                NJ_UCC_STEP_SEARCH_FIELD: "Search",
            }
        )
        results = client.post(NJ_UCC_SEARCH_URL, data=data)
        results.raise_for_status()
    return parse_new_jersey_ucc_results(results.text)


def to_public_search_results(
    company_name: str, rows: list[NewJerseyUccSearchResult]
) -> list[PublicSearchUccResult]:
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    mapped = []
    for row in rows:
        mapped.append(
            PublicSearchUccResult(
                state="NJ",
                filing_id=row.filing_number,
                debtor_name=row.organization_name,
                filing_type="UCC1",
                status=row.status,
                search_query=query,
                source_url=NJ_UCC_SEARCH_URL,
                filing_date=row.filing_date,
                debtor_city=row.city,
                debtor_state="NJ",
                collateral_description="New Jersey public UCC status-search summary",
                match_confidence=_confidence(query_normalized, row.organization_name),
            )
        )
    return mapped


def parse_new_jersey_ucc_results(html: str) -> list[NewJerseyUccSearchResult]:
    parser = _ResultsTableParser()
    parser.feed(html)
    rows = []
    for cells in parser.rows:
        if len(cells) < 8 or cells[1].lower() == "organization":
            continue
        filing_number = cells[3]
        if not filing_number.isdigit():
            continue
        rows.append(
            NewJerseyUccSearchResult(
                organization_name=cells[1],
                city=cells[2] or None,
                filing_number=filing_number,
                status=cells[4],
                filing_date=_parse_date(cells[5]),
                page_count=_parse_int(cells[7]),
            )
        )
    return rows


def _hidden_fields(html: str) -> dict[str, str]:
    parser = _HiddenFieldParser()
    parser.feed(html)
    return parser.fields


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    return 70


def _parse_date(value: str) -> date | None:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_int(value: str) -> int | None:
    try:
        return int(value.strip())
    except ValueError:
        return None


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


class _ResultsTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_results_table = False
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "table" and values.get("id", "").endswith("orgResultsGridView"):
            self.in_results_table = True
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
            self.rows.append(self.current_row)
        elif self.in_results_table and tag == "table":
            self.in_results_table = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if self.in_cell and text:
            self.current_cell.append(text)
