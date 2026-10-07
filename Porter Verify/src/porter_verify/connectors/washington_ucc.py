"""Washington UCC file ingestion helpers.

The current public Washington pages expose UCC search/filing, but no verified
direct bulk URL is hard-coded here. This connector ingests an official CSV/JSON
export when a file or URL is supplied.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from porter_verify.db.models import UccFiling
from porter_verify.services.ucc_intelligence import apply_lender_classification, normalize_ucc_name


def ingest_washington_ucc_file(
    session: Session, path: str | Path, *, batch_size: int = 1_000, limit: int | None = None
) -> int:
    count = 0
    pending: list[UccFiling] = []
    for row in _rows(Path(path)):
        if limit is not None and count >= limit:
            break
        filing = _filing_from_row(row)
        if filing is None:
            continue
        apply_lender_classification(session, filing)
        pending.append(filing)
        count += 1
        if len(pending) >= batch_size:
            _upsert(session, pending)
            pending.clear()
    _upsert(session, pending)
    session.commit()
    return count


def _rows(path: Path) -> Iterator[dict]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, list):
            yield from data
        else:
            yield from data.get("data", [])
        return
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        yield from csv.DictReader(handle)


def _filing_from_row(row: dict) -> UccFiling | None:
    filing_id = _first(row, "filing_id", "filing number", "file_number", "ucc_number")
    debtor_name = _first(row, "debtor_name", "debtor", "organization_name", "name")
    if not filing_id or not debtor_name:
        return None
    filing_type = _filing_type(_first(row, "filing_type", "type", "transaction_type"))
    state = (_first(row, "state", "source_state") or "WA").upper()[:2]
    secured_party = _first(row, "secured_party_name", "secured party", "secured_party")
    filing_date = _parse_date(_first(row, "filing_date", "file_date", "date_filed"))
    termination_date = _parse_date(_first(row, "termination_date", "terminated_date"))
    status = _status(_first(row, "status", "lien_status"), filing_type, termination_date)
    return UccFiling(
        id=f"{state}:{filing_id}",
        filing_id=filing_id,
        state=state,
        filing_type=filing_type,
        debtor_name=debtor_name,
        debtor_normalized=normalize_ucc_name(debtor_name),
        debtor_address=_first(row, "debtor_address", "address"),
        debtor_city=_first(row, "debtor_city", "city"),
        debtor_state=_first(row, "debtor_state", "state_code"),
        debtor_zip=_first(row, "debtor_zip", "zip", "zipcode"),
        secured_party_name=secured_party,
        secured_party_normalized=normalize_ucc_name(secured_party),
        collateral_description=_first(row, "collateral_description", "collateral"),
        filing_date=filing_date,
        termination_date=termination_date,
        status=status,
        lender_type="UNKNOWN",
        is_factoring_related=False,
        is_mca_related=False,
        source_state=state,
        source_url=_first(row, "source_url", "url"),
    )


def _upsert(session: Session, filings: list[UccFiling]) -> None:
    for filing in filings:
        session.merge(filing)
    session.flush()


def _first(row: dict, *names: str) -> str | None:
    lowered = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%m%d%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _filing_type(value: str | None) -> str:
    text = normalize_ucc_name(value)
    if "TERMIN" in text or "UCC3" in text:
        return "UCC3"
    if "CONTINU" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _status(value: str | None, filing_type: str, termination_date: date | None) -> str:
    text = normalize_ucc_name(value)
    if filing_type == "UCC3" or termination_date is not None or "TERMIN" in text:
        return "TERMINATED"
    if "AMEND" in text:
        return "AMENDED"
    return "ACTIVE"
