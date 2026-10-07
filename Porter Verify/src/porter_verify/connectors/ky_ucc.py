"""Targeted Kentucky UCC public-search connector.

Kentucky UCC search is an ASP.NET WebForms application at:
  https://web.sos.ky.gov/ftucc/search.aspx

The site uses session tokens embedded as path segments:
  /ftucc/(S(sessionid))/search.aspx

CONFIRMED WORKING (2026-07-03, live test) via plain httpx (no Playwright
needed -- no bot-detection or CAPTCHA encountered):

1. GET the base search URL; ASP.NET redirects to a session-scoped URL.
2. POST the organization-name field. Real field name (differs from an
   earlier version of this connector, which used "OrgName"):
       ctl00$ContentPlaceHolder1$SearchForm1$tOrgname
   Submit field: ctl00$ContentPlaceHolder1$SearchForm1$bSearch = "Search"
3. The response contains up to TWO result tables that must both be parsed
   and combined:
     - "A standard search revealed the following N results"
       (id=..._searchlist1_Table1)
     - "A non-standard search revealed the following N additional results"
       (fuzzy/phonetic matches; id=..._searchlist2_Table1)
   Real column order (5 columns, confirmed live -- no filing-type or
   city/state/zip columns exist in this view, contrary to an earlier
   version of this connector):
       [Debtor Name, File Number, File Date and Time, Lapse Date, Secured Party]

The Bulk Data Service at secure.kentucky.gov/sos/bulkdata/ requires an
OIDC-authenticated Kentucky.gov account and a $1,500/month commercial
subscription -- not suitable for a free connector. This connector uses the
public targeted search only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser

import httpx

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

KY_UCC_BASE_URL = "https://web.sos.ky.gov/ftucc/search.aspx"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
_TIMEOUT = 30
_ORG_NAME_FIELD = "ctl00$ContentPlaceHolder1$SearchForm1$tOrgname"
_SEARCH_BUTTON_FIELD = "ctl00$ContentPlaceHolder1$SearchForm1$bSearch"


@dataclass(frozen=True)
class KentuckyUccSearchResult:
    filing_number: str
    debtor_name: str
    filing_date: date | None
    lapse_date: date | None
    secured_party: str | None


def search_ky_ucc(company_name: str) -> list[KentuckyUccSearchResult]:
    """Search Kentucky UCC filings by organization (debtor) name."""
    query = company_name.strip()

    with httpx.Client(
        follow_redirects=True,
        timeout=_TIMEOUT,
        headers={"User-Agent": _USER_AGENT, "Referer": KY_UCC_BASE_URL},
    ) as client:
        first = client.get(KY_UCC_BASE_URL)
        first.raise_for_status()
        session_url = str(first.url)

        hidden = _hidden_fields(first.text)
        hidden.update(
            {
                _ORG_NAME_FIELD: query,
                _SEARCH_BUTTON_FIELD: "Search",
            }
        )

        results = client.post(session_url, data=hidden)
        results.raise_for_status()

    return _parse_ky_results(results.text)


def to_public_search_results(
    company_name: str, rows: list[KentuckyUccSearchResult]
) -> list[PublicSearchUccResult]:
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    mapped = []
    for row in rows:
        status = _derive_status(row.lapse_date)
        mapped.append(
            PublicSearchUccResult(
                state="KY",
                filing_id=row.filing_number,
                debtor_name=row.debtor_name,
                filing_type="UCC1",
                status=status,
                search_query=query,
                source_url=KY_UCC_BASE_URL,
                secured_party_name=row.secured_party,
                filing_date=row.filing_date,
                termination_date=None,
                debtor_city=None,
                debtor_state="KY",
                debtor_zip=None,
                collateral_description=None,
                match_confidence=_confidence(query_normalized, row.debtor_name),
            )
        )
    return mapped


def _parse_ky_results(html: str) -> list[KentuckyUccSearchResult]:
    """Parse both the standard-match and non-standard-match result tables.

    Live-confirmed column order: Debtor Name, File Number, File Date and
    Time, Lapse Date, Secured Party (5 columns; no filing-type column
    exists in this view).
    """
    parser = _ResultsTableParser()
    parser.feed(html)
    rows: list[KentuckyUccSearchResult] = []
    seen_filing_numbers: set[str] = set()
    for cells in parser.rows:
        if len(cells) < 5:
            continue
        debtor_name = cells[0].strip()
        if not debtor_name or debtor_name.lower().replace("\xa0", " ").strip() in {
            "debtor name",
            "debtor  name",
        }:
            continue
        filing_number = cells[1].strip()
        if not filing_number or filing_number in seen_filing_numbers:
            continue
        seen_filing_numbers.add(filing_number)

        rows.append(
            KentuckyUccSearchResult(
                filing_number=filing_number,
                debtor_name=debtor_name,
                filing_date=_parse_date(cells[2]),
                lapse_date=_parse_date(cells[3]),
                secured_party=cells[4].strip() or None if len(cells) > 4 else None,
            )
        )
    return rows


def _hidden_fields(html: str) -> dict[str, str]:
    parser = _HiddenFieldParser()
    parser.feed(html)
    return parser.fields


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


def _derive_status(lapse_date: date | None) -> str:
    if lapse_date is not None and lapse_date < date.today():
        return "TERMINATED"
    return "ACTIVE"


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    return 70


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
    """Parse every KY results table (id contains "searchlist") and combine rows.

    KY renders up to two separate result tables (standard + non-standard
    matches), both with id like "..._searchlist1_Table1" /
    "..._searchlist2_Table1" -- neither contains "grid"/"result"/"ucc",
    so detection must match on "searchlist" specifically.
    """

    def __init__(self) -> None:
        super().__init__()
        self._in_table = False
        self._depth = 0
        self._in_cell = False
        self._current_cell: list[str] = []
        self._current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        if tag == "table":
            table_id = attr_dict.get("id", "").lower()
            if not self._in_table and "searchlist" in table_id:
                self._in_table = True
                self._depth = 1
            elif self._in_table:
                self._depth += 1
        elif self._in_table and tag == "tr":
            self._current_row = []
        elif self._in_table and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if self._in_table and tag in {"td", "th"} and self._in_cell:
            self._current_row.append(" ".join(self._current_cell).strip())
            self._in_cell = False
            self._current_cell = []
        elif self._in_table and tag == "tr" and self._current_row:
            self.rows.append(self._current_row)
            self._current_row = []
        elif tag == "table" and self._in_table:
            self._depth -= 1
            if self._depth <= 0:
                self._in_table = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if self._in_cell and text:
            self._current_cell.append(text)
