"""Florida UCC filing ingestion from Florida Secured Transaction Registry downloads."""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from porter_verify.db.base import utcnow
from porter_verify.db.models import UccFiling
from porter_verify.services.ucc_intelligence import apply_lender_classification, normalize_ucc_name

FL_UCC_DOWNLOAD_API_URL = "https://publicsearchapi.floridaucc.com/Downloads"
FL_UCC_SOURCE_URL = "https://floridaucc.com/download"
FL_UCC_SEARCH_URL = "https://floridaucc.com/search"
FL_UCC_FILE_TYPES = ("Filings", "Debtors", "Secureds", "Events")


def download_fl_ucc_zips(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for file_type in FL_UCC_FILE_TYPES:
        response = httpx.get(
            FL_UCC_DOWNLOAD_API_URL,
            params={"downloadType": "Full", "fileType": file_type},
            timeout=60,
            follow_redirects=True,
            headers={"Origin": "https://floridaucc.com", "Referer": "https://floridaucc.com/"},
        )
        response.raise_for_status()
        payload = response.json()["payload"]
        request = Request(payload, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=300) as source, (  # noqa: S310
            target_dir / f"{file_type.lower()}_full.zip"
        ).open("wb") as destination:
            while chunk := source.read(1024 * 1024):
                destination.write(chunk)


def ingest_fl_ucc_zip_dir(
    session: Session,
    zip_dir: Path,
    *,
    limit: int | None = None,
    batch_size: int = 1_000,
) -> int:
    wanted_ids = _wanted_filing_ids(zip_dir)
    debtors = _first_parties(zip_dir / "debtors_full.zip", wanted_ids, "Deb")
    secureds = _first_parties(zip_dir / "secureds_full.zip", wanted_ids, "Sec")
    count = 0
    pending: list[dict] = []

    for filing in _active_filings(zip_dir, debtors, secureds):
        apply_lender_classification(session, filing)
        pending.append(_filing_dict(filing))
        count += 1
        if len(pending) >= batch_size:
            _upsert(session, pending)
            session.commit()
            pending.clear()
        if limit is not None and count >= limit:
            break

    if limit is None or count < limit:
        for filing in _termination_filings(zip_dir, debtors, secureds):
            apply_lender_classification(session, filing)
            pending.append(_filing_dict(filing))
            count += 1
            if len(pending) >= batch_size:
                _upsert(session, pending)
                session.commit()
                pending.clear()
            if limit is not None and count >= limit:
                break

    _upsert(session, pending)
    session.commit()
    return count


def _wanted_filing_ids(zip_dir: Path) -> set[str]:
    wanted: set[str] = set()
    for row in _zip_rows(zip_dir / "filings_full.zip"):
        if _first(row, "FilingStatus") == "Filed":
            wanted.add(_filing_key(_first(row, "Ucc1FilingNumber")))
    for row in _zip_rows(zip_dir / "events_full.zip"):
        if _event_is_termination(row):
            wanted.add(_filing_key(_first(row, "Ucc1FilingNumber")))
    return wanted


def _first_parties(zip_path: Path, wanted_ids: set[str], prefix: str) -> dict[str, dict]:
    parties: dict[str, dict] = {}
    id_column = "Ucc1FilingNumber"
    name_column = f"{prefix}Name"
    for row in _zip_rows(zip_path):
        filing_key = _filing_key(_first(row, id_column))
        if filing_key not in wanted_ids or filing_key in parties:
            continue
        if _first(row, name_column):
            parties[filing_key] = row
    return parties


def _active_filings(
    zip_dir: Path,
    debtors: dict[str, dict],
    secureds: dict[str, dict],
) -> Iterator[UccFiling]:
    for row in _zip_rows(zip_dir / "filings_full.zip"):
        if _first(row, "FilingStatus") != "Filed":
            continue
        filing_id = _first(row, "Ucc1FilingNumber")
        filing_key = _filing_key(filing_id)
        debtor = debtors.get(filing_key)
        if not filing_id or debtor is None:
            continue
        secured = secureds.get(filing_key, {})
        debtor_name = _first(debtor, "DebName")
        if not debtor_name:
            continue
        secured_name = _first(secured, "SecName")
        yield UccFiling(
            id=f"FL:UCC1:{filing_id}",
            filing_id=filing_id,
            state="FL",
            filing_type="UCC1",
            debtor_name=debtor_name,
            debtor_normalized=normalize_ucc_name(debtor_name),
            debtor_address=_join(
                _first(debtor, "DebAddressLine1"),
                _first(debtor, "DebAddressLine2"),
            ),
            debtor_city=_first(debtor, "DebCity"),
            debtor_state=_first(debtor, "DebState"),
            debtor_zip=_first(debtor, "DebZipCode"),
            secured_party_name=secured_name,
            secured_party_normalized=normalize_ucc_name(secured_name),
            collateral_description="Florida UCC financing statement",
            filing_date=_parse_date(_first(row, "FilingDate")),
            termination_date=None,
            status="ACTIVE",
            lender_type="UNKNOWN",
            is_factoring_related=False,
            is_mca_related=False,
            source_state="FL",
            source_url=FL_UCC_SEARCH_URL,
        )


def _termination_filings(
    zip_dir: Path,
    debtors: dict[str, dict],
    secureds: dict[str, dict],
) -> Iterator[UccFiling]:
    for row in _zip_rows(zip_dir / "events_full.zip"):
        if not _event_is_termination(row):
            continue
        ucc3_id = _first(row, "Ucc3FilingNumber")
        original_id = _first(row, "Ucc1FilingNumber")
        filing_key = _filing_key(original_id)
        debtor = debtors.get(filing_key)
        if not ucc3_id or debtor is None:
            continue
        secured = secureds.get(filing_key, {})
        debtor_name = _first(debtor, "DebName")
        if not debtor_name:
            continue
        secured_name = _first(secured, "SecName")
        event_date = _parse_date(_first(row, "EventDate"))
        yield UccFiling(
            id=f"FL:UCC3:{ucc3_id}",
            filing_id=ucc3_id,
            state="FL",
            filing_type="UCC3",
            debtor_name=debtor_name,
            debtor_normalized=normalize_ucc_name(debtor_name),
            debtor_address=_join(
                _first(debtor, "DebAddressLine1"),
                _first(debtor, "DebAddressLine2"),
            ),
            debtor_city=_first(debtor, "DebCity"),
            debtor_state=_first(debtor, "DebState"),
            debtor_zip=_first(debtor, "DebZipCode"),
            secured_party_name=secured_name,
            secured_party_normalized=normalize_ucc_name(secured_name),
            collateral_description=_first(row, "ActionVerbage"),
            filing_date=event_date,
            termination_date=event_date,
            status="TERMINATED",
            lender_type="UNKNOWN",
            is_factoring_related=False,
            is_mca_related=False,
            source_state="FL",
            source_url=FL_UCC_SEARCH_URL,
        )


def _zip_rows(zip_path: Path) -> Iterator[dict]:
    with zipfile.ZipFile(zip_path) as archive:
        name = archive.namelist()[0]
        with archive.open(name) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
            yield from csv.DictReader(text, delimiter="|")


def _upsert(session: Session, rows: list[dict]) -> None:
    if not rows:
        return
    table = UccFiling.__table__
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        statement = sqlite_insert(table).values(rows)
    elif dialect == "postgresql":
        statement = pg_insert(table).values(rows)
    else:
        for row in rows:
            session.merge(UccFiling(**row))
        return
    excluded = statement.excluded
    updates = {
        column.name: getattr(excluded, column.name)
        for column in table.columns
        if column.name not in {"id", "created_at", "updated_at"}
    }
    updates["updated_at"] = utcnow()
    session.execute(statement.on_conflict_do_update(index_elements=[table.c.id], set_=updates))


def _filing_dict(filing: UccFiling) -> dict:
    return {
        "id": filing.id,
        "filing_id": filing.filing_id,
        "state": filing.state,
        "filing_type": filing.filing_type,
        "debtor_name": filing.debtor_name,
        "debtor_normalized": filing.debtor_normalized,
        "debtor_address": filing.debtor_address,
        "debtor_city": filing.debtor_city,
        "debtor_state": filing.debtor_state,
        "debtor_zip": filing.debtor_zip,
        "secured_party_name": filing.secured_party_name,
        "secured_party_normalized": filing.secured_party_normalized,
        "collateral_description": filing.collateral_description,
        "filing_date": filing.filing_date,
        "termination_date": filing.termination_date,
        "status": filing.status,
        "lender_type": filing.lender_type,
        "is_factoring_related": filing.is_factoring_related,
        "is_mca_related": filing.is_mca_related,
        "source_state": filing.source_state,
        "source_url": filing.source_url,
    }


def _first(row: dict, *names: str) -> str | None:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _filing_key(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lstrip("0") or "0"


def _event_is_termination(row: dict) -> bool:
    text = normalize_ucc_name(_first(row, "ActionVerbage"))
    return text in {"TERMINATION", "RELEASE"}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(value[:23], fmt).date()
        except ValueError:
            continue
    return None


def _join(*parts: str | None) -> str | None:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    return " ".join(cleaned) or None
