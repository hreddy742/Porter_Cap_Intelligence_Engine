"""Targeted Idaho UCC public-search connector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import httpx

from porter_verify.services.ucc_intelligence import normalize_ucc_name
from porter_verify.services.ucc_public_search import PublicSearchUccResult

ID_UCC_SEARCH_URL = "https://sosbiz.idaho.gov/search/ucc"
ID_UCC_SEARCH_API_URL = "https://sosbiz.idaho.gov/api/records/uccinforeqsearch"


@dataclass(frozen=True)
class IdahoUccSearchResult:
    debtor_name: str
    filing_number: str
    secured_party: str | None
    status: str
    filing_date: date | None
    lien_type: str


def search_idaho_ucc(company_name: str) -> list[IdahoUccSearchResult]:
    payload = _payload(company_name)
    with httpx.Client(
        follow_redirects=True,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": ID_UCC_SEARCH_URL,
        },
    ) as client:
        response = client.post(ID_UCC_SEARCH_API_URL, json=payload)
        response.raise_for_status()
    rows = response.json().get("rows", {})
    return [_result_from_row(row) for row in rows.values()]


def to_public_search_results(
    company_name: str, rows: list[IdahoUccSearchResult]
) -> list[PublicSearchUccResult]:
    query = company_name.strip()
    query_normalized = normalize_ucc_name(query)
    return [
        PublicSearchUccResult(
            state="ID",
            filing_id=row.filing_number,
            debtor_name=row.debtor_name,
            filing_type=_filing_type(row.lien_type),
            status=row.status,
            search_query=query,
            source_url=ID_UCC_SEARCH_URL,
            secured_party_name=row.secured_party,
            filing_date=row.filing_date,
            collateral_description="Idaho public UCC status-search summary",
            match_confidence=_confidence(query_normalized, row.debtor_name),
        )
        for row in rows
    ]


def _payload(company_name: str) -> dict:
    return {
        "SEC_PARTY_SEARCH_YN": False,
        "SEARCH_IS_ORG": True,
        "SEARCH_LAST_NAME": "",
        "SEARCH_FIRST_NAME": "",
        "SEARCH_MIDDLE_NAME": "",
        "SEARCH_SUFFIX": "",
        "SEARCH_ORG_NAME": company_name,
        "SEARCH_CITY": "",
        "SEARCH_STATE": "",
        "SEARCH_LAPSED": False,
        "SEARCH_TYPE": "DEBTOR",
        "SEARCH_REQUEST_TYPE": "LIST_ONLY",
        "SEARCH_UCC": True,
        "SEARCH_GOV": False,
        "SEARCH_EFS": False,
        "SEARCH_CROP_LIEN": False,
        "SEARCH_AG_LIEN": False,
        "SEARCH_MODE": 4,
        "SEARCH_UCC_NUM": "",
        "BEGIN_DATE": "",
    }


def _result_from_row(row: dict) -> IdahoUccSearchResult:
    title = row.get("TITLE") or []
    debtor = title[0] if isinstance(title, list) and title else str(title or "")
    return IdahoUccSearchResult(
        debtor_name=_debtor_name(debtor),
        filing_number=str(row.get("RECORD_NUM") or "").strip(),
        secured_party=(row.get("SEC_PARTY") or None),
        status=str(row.get("STATUS") or "ACTIVE").strip(),
        filing_date=_parse_date(row.get("FILING_DATE")),
        lien_type=str(row.get("RECORD_TYPE") or "Initial").strip(),
    )


def _debtor_name(value: str) -> str:
    return value.split(" - ", 1)[0].strip()


def _filing_type(value: str) -> str:
    text = normalize_ucc_name(value)
    if "TERMIN" in text or "RELEASE" in text:
        return "UCC3"
    if "AMEND" in text:
        return "AMENDMENT"
    if "CONTINU" in text:
        return "CONTINUATION"
    return "UCC1"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _confidence(query_normalized: str, debtor_name: str) -> int:
    debtor_normalized = normalize_ucc_name(debtor_name)
    if debtor_normalized == query_normalized:
        return 100
    if query_normalized and query_normalized in debtor_normalized:
        return 90
    return 70
