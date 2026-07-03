"""Targeted Missouri UCC public-search connector.

Missouri UCC filings are managed exclusively by the Secretary of State's
Business Services Division at:

    https://bsd.sos.mo.gov/LoginWelcome.aspx?lobID=0

Unlike states such as NJ or KY, Missouri does NOT expose a free,
unauthenticated "type a company name, get results" public search page.
Findings from live research (2026-07-02):

  * There is no Socrata / open-data bulk dataset for MO UCC filings
    (data.mo.gov has zero UCC datasets) and no bulk CSV/FTP program.
  * The bsd.sos.mo.gov search portal requires a registered "Corporate
    E-account". Registration requires an ACH authorization form with an
    original wet signature and a ~7-business-day bank pre-note period
    before the account is usable -- this cannot be automated end-to-end
    and is not something a script can complete on its own.
  * The domain returns HTTP 403 to plain automated HTTP clients that
    lack full browser headers/session state, consistent with an
    authenticated, session-gated application rather than a public
    ASP.NET form that can be driven anonymously.
  * Because no authenticated session exists in this environment, and the
    post-login search form has never actually been observed, we do not
    know the real control names for the debtor-name field or the
    __VIEWSTATE/__EVENTVALIDATION-bearing results page that follows
    login. Shipping a connector that guesses ASP.NET control IDs would
    either fail outright or, worse, silently return wrong/no data while
    looking like it succeeded.

Given that, this connector intentionally does NOT attempt an
unauthenticated scrape of a guessed search URL. `search_mo_ucc()` probes
the one URL we do know (the public login entry point), and always raises
`MissouriUccAuthRequiredError` describing exactly what is required to
unlock real access:

  * A Corporate E-account (ACH-backed) provisioned by the SOS UCC
    Division, or
  * A negotiated bulk/data-licensing arrangement with the MO SOS UCC
    Division (573-751-4628 or 866-223-6535 opt 4) -- they report
    processing ~30,000 information requests/year and may have an
    arrangement not documented publicly.

Once Porter Verify obtains either of those and can capture real,
authenticated search-results HTML, replace `search_mo_ucc()` with a real
Selenium/Playwright (or authenticated-session httpx) implementation
modeled on ky_ucc.py / new_jersey_ucc.py, and fill in
`parse_missouri_ucc_results()` against the actual observed markup.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser

import httpx

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

MO_UCC_LOGIN_URL = "https://bsd.sos.mo.gov/LoginWelcome.aspx?lobID=0"
_USER_AGENT = "Mozilla/5.0 (compatible; PorterVerify/1.0)"
_TIMEOUT = 30


class MissouriUccAuthRequiredError(RuntimeError):
    """Raised when MO UCC search is attempted without an authenticated session.

    Missouri's SOS UCC search portal (bsd.sos.mo.gov) requires a registered
    Corporate E-account (ACH-backed, ~7 business day setup) before any
    debtor-name search can be performed. There is no public, unauthenticated
    search endpoint or bulk-download alternative.
    """


@dataclass(frozen=True)
class MissouriUccSearchResult:
    """Shape for a parsed MO UCC search-result row.

    Field order/names are best-effort, modeled on typical SOS UCC search
    grids (see ky_ucc.py), and are NOT yet verified against real MO output
    since that requires an authenticated session this environment does not
    have. Revisit once real authenticated HTML has been captured.
    """

    filing_number: str
    debtor_name: str
    filing_date: date | None
    lapse_date: date | None
    filing_type: str
    status: str
    debtor_city: str | None
    debtor_state_abbr: str | None
    debtor_zip: str | None


def search_mo_ucc(company_name: str) -> list[MissouriUccSearchResult]:
    """Attempt a Missouri UCC debtor-name search.

    Missouri's UCC search portal is authentication-gated (Corporate
    E-account with ACH pre-note). This function performs a lightweight
    reachability probe of the one known public entry point so failures
    are diagnosable (network vs. auth-wall), then always raises
    `MissouriUccAuthRequiredError` because no unauthenticated search path
    is known to exist. This is intentional: we do not guess ASP.NET field
    names for a form we have never observed as an authenticated user.
    """
    query = company_name.strip()
    if not query:
        raise ValueError("company_name must not be empty")

    status: int | None = None
    with httpx.Client(
        follow_redirects=True,
        timeout=_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        try:
            response = client.get(MO_UCC_LOGIN_URL)
            status = response.status_code
        except httpx.HTTPError as exc:
            raise MissouriUccAuthRequiredError(
                "Missouri UCC search portal (bsd.sos.mo.gov) was unreachable "
                f"({exc}) and in any case requires an authenticated "
                "Corporate E-account before any search can be performed."
            ) from exc

    raise MissouriUccAuthRequiredError(
        "Missouri UCC filings cannot be searched without a registered "
        "Corporate E-account at bsd.sos.mo.gov (ACH-backed, ~7 business "
        f"day setup). Probe of {MO_UCC_LOGIN_URL} returned HTTP {status}. "
        "There is no public bulk dataset (data.mo.gov has zero UCC "
        "datasets) and no free-form public search for MO UCC data. "
        "Contact the MO SOS UCC Division at (573) 751-4628 or "
        "(866) 223-6535 opt 4 to request Corporate E-account access or a "
        "bulk/data-licensing arrangement, then implement a real "
        "authenticated session (Selenium/Playwright recommended) in this "
        "module."
    )


def to_public_search_results(
    company_name: str, rows: list[MissouriUccSearchResult]
) -> list[PublicSearchUccResult]:
    """Map parsed MO rows to the shared PublicSearchUccResult shape.

    Kept for interface parity with other targeted-search connectors, and
    for use once `search_mo_ucc` / `parse_missouri_ucc_results` are
    implemented against a real authenticated session. Currently only
    reachable with an empty `rows` list since `search_mo_ucc` always
    raises `MissouriUccAuthRequiredError` before returning any rows.
    """
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    mapped = []
    for row in rows:
        mapped.append(
            PublicSearchUccResult(
                state="MO",
                filing_id=row.filing_number,
                debtor_name=row.debtor_name,
                filing_type=row.filing_type,
                status=row.status,
                search_query=query,
                source_url=MO_UCC_LOGIN_URL,
                filing_date=row.filing_date,
                termination_date=row.lapse_date if row.status == "TERMINATED" else None,
                debtor_city=row.debtor_city,
                debtor_state=row.debtor_state_abbr,
                debtor_zip=row.debtor_zip,
                collateral_description=None,
                match_confidence=_confidence(query_normalized, row.debtor_name),
            )
        )
    return mapped


# ---------------------------------------------------------------------------
# HTML parsing helpers (unverified -- awaiting authenticated-session access)
# ---------------------------------------------------------------------------

def parse_missouri_ucc_results(html: str) -> list[MissouriUccSearchResult]:
    """Parse an MO UCC search-results HTML page.

    NOT YET VALIDATED against real output -- bsd.sos.mo.gov requires an
    authenticated Corporate E-account session, which this environment
    does not have. The table-scan heuristic below mirrors the approach
    used for other SOS ASP.NET UCC portals (see ky_ucc.py) and should be
    revisited once real authenticated HTML can be captured.
    """
    parser = _ResultsTableParser()
    parser.feed(html)
    rows: list[MissouriUccSearchResult] = []
    for cells in parser.rows:
        if len(cells) < 4:
            continue
        first_cell = cells[0].strip()
        if first_cell.lower() in {"filing", "file", "filing number", "#", ""}:
            continue

        filing_number = _cell(cells, 0)
        debtor_name = _cell(cells, 1)
        if not filing_number or not debtor_name:
            continue

        file_date = _parse_date(_cell(cells, 2))
        lapse_date = _parse_date(_cell(cells, 3))
        raw_type = _cell(cells, 4)
        city = _cell(cells, 5) or None
        state_abbr = _cell(cells, 6) or None
        zip_code = _cell(cells, 7) or None

        filing_type = _map_filing_type(raw_type)
        status = _derive_status(lapse_date, filing_type)

        rows.append(
            MissouriUccSearchResult(
                filing_number=filing_number,
                debtor_name=debtor_name,
                filing_date=file_date,
                lapse_date=lapse_date,
                filing_type=filing_type,
                status=status,
                debtor_city=city,
                debtor_state_abbr=state_abbr,
                debtor_zip=zip_code,
            )
        )
    return rows


def _cell(cells: list[str], index: int) -> str:
    try:
        return cells[index].strip()
    except IndexError:
        return ""


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _map_filing_type(raw: str) -> str:
    upper = raw.upper()
    if "TERM" in upper or "RELEASE" in upper:
        return "UCC3"
    if "CONTINU" in upper:
        return "CONTINUATION"
    if "AMEND" in upper:
        return "AMENDMENT"
    if "UCC3" in upper or "3" in upper:
        return "UCC3"
    return "UCC1"


def _derive_status(lapse_date: date | None, filing_type: str) -> str:
    if filing_type == "UCC3":
        return "TERMINATED"
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


class _ResultsTableParser(HTMLParser):
    """Parse the first HTML table that appears to contain UCC filing rows."""

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
            table_id = attr_dict.get("id", "")
            if not self._in_table and (
                "grid" in table_id.lower()
                or "result" in table_id.lower()
                or "ucc" in table_id.lower()
            ):
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
