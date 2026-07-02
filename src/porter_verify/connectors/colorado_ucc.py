"""Colorado UCC ingestion from official data.colorado.gov Socrata datasets."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from porter_verify.db.base import utcnow
from porter_verify.db.models import UccFiling
from porter_verify.services.ucc_intelligence import apply_lender_classification, normalize_ucc_name

CO_UCC_FILING_API_URL = "https://data.colorado.gov/resource/wffy-3uut.json"
CO_UCC_DEBTOR_API_URL = "https://data.colorado.gov/resource/8upq-58vz.json"
CO_UCC_SECURED_PARTY_API_URL = "https://data.colorado.gov/resource/ap62-sav4.json"
CO_UCC_COLLATERAL_API_URL = "https://data.colorado.gov/resource/4am6-w6u4.json"
CO_UCC_SOURCE_URL = "https://data.colorado.gov/Business/Uniform-Commercial-Code-UCC-Filing-Information-in-/wffy-3uut"

FILING_FIELDS = (
    "transactionid",
    "masterdocumentid",
    "transactiontype",
    "filingdate",
    "lapsedate",
    "filingtype",
    "documenttype",
    "continuation",
    "terminationflag",
    "fileid",
)


def fetch_co_ucc_rows(*, page_size: int = 50_000, limit: int | None = None) -> Iterator[dict]:
    offset = 0
    emitted = 0
    with httpx.Client(
        timeout=120, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}
    ) as client:
        while True:
            remaining = None if limit is None else limit - emitted
            if remaining is not None and remaining <= 0:
                return
            batch_limit = min(page_size, remaining) if remaining is not None else page_size
            response = client.get(
                CO_UCC_FILING_API_URL,
                params={
                    "$select": ",".join(FILING_FIELDS),
                    "$limit": batch_limit,
                    "$offset": offset,
                    "$order": "fileid",
                },
            )
            response.raise_for_status()
            filings = response.json()
            if not filings:
                return
            related = _related_by_fileid(
                client,
                [filing["fileid"] for filing in filings if filing.get("fileid")],
            )
            for filing in filings:
                fileid = filing.get("fileid")
                if not fileid:
                    continue
                filing["debtor"] = related["debtor"].get(fileid)
                filing["secured_party"] = related["secured_party"].get(fileid)
                filing["collateral"] = related["collateral"].get(fileid)
                yield filing
            emitted += len(filings)
            offset += len(filings)


def ingest_co_ucc_rows(
    session: Session,
    rows: Iterator[dict],
    *,
    batch_size: int = 1_000,
) -> int:
    count = 0
    pending: list[dict] = []
    for row in rows:
        filing = _filing_from_row(row)
        if filing is None:
            continue
        apply_lender_classification(session, filing)
        pending.append(_filing_dict(filing))
        count += 1
        if len(pending) >= batch_size:
            _upsert(session, pending)
            session.commit()
            pending.clear()
    _upsert(session, pending)
    session.commit()
    return count


def ingest_co_ucc_csv_dir(
    session: Session,
    directory: str | Path,
    *,
    batch_size: int = 1_000,
    limit: int | None = None,
) -> int:
    directory = Path(directory)
    debtor_by_fileid = _index_related_csv(directory / "debtor.csv")
    secured_party_by_fileid = _index_related_csv(directory / "secured_party.csv")
    collateral_by_fileid = _index_related_csv(directory / "collateral.csv")

    def rows() -> Iterator[dict]:
        with (directory / "filing.csv").open(
            encoding="utf-8-sig", errors="replace", newline=""
        ) as handle:
            for row in csv.DictReader(handle):
                fileid = _first(row, "fileid", "fileId")
                if not fileid:
                    continue
                row["debtor"] = debtor_by_fileid.get(fileid)
                row["secured_party"] = secured_party_by_fileid.get(fileid)
                row["collateral"] = collateral_by_fileid.get(fileid)
                yield row

    if limit is None:
        return ingest_co_ucc_rows(session, rows(), batch_size=batch_size)
    return ingest_co_ucc_rows(session, _limited(rows(), limit), batch_size=batch_size)


def _related_by_fileid(client: httpx.Client, fileids: list[str]) -> dict[str, dict[str, dict]]:
    return {
        "debtor": _fetch_related_batch(client, CO_UCC_DEBTOR_API_URL, fileids),
        "secured_party": _fetch_related_batch(client, CO_UCC_SECURED_PARTY_API_URL, fileids),
        "collateral": _fetch_related_batch(client, CO_UCC_COLLATERAL_API_URL, fileids),
    }


def _fetch_related_batch(client: httpx.Client, url: str, fileids: list[str]) -> dict[str, dict]:
    by_fileid: dict[str, dict] = {}
    for chunk in _chunks(fileids, 200):
        quoted = ",".join(f"'{fileid}'" for fileid in chunk)
        response = client.get(
            url,
            params={
                "$limit": 50_000,
                "$where": f"fileid in({quoted})",
                "$order": "recordstatus DESC",
            },
        )
        response.raise_for_status()
        for row in response.json():
            fileid = row.get("fileid")
            if fileid and fileid not in by_fileid:
                by_fileid[fileid] = row
    return by_fileid


def _chunks(values: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _filing_from_row(row: dict) -> UccFiling | None:
    filing_id = _first(row, "transactionid", "transactionId")
    debtor = row.get("debtor") or {}
    secured_party = row.get("secured_party") or {}
    collateral = row.get("collateral") or {}
    debtor_name = _name(debtor)
    if not filing_id or not debtor_name:
        return None
    secured_party_name = _name(secured_party)
    filing_type = _filing_type(row)
    filing_date = _parse_date(_first(row, "filingdate", "filingDate"))
    termination_date = filing_date if filing_type == "UCC3" else None
    return UccFiling(
        id=f"CO:{filing_id}",
        filing_id=filing_id,
        state="CO",
        filing_type=filing_type,
        debtor_name=debtor_name,
        debtor_normalized=normalize_ucc_name(debtor_name),
        debtor_address=_join(_first(debtor, "address1"), _first(debtor, "address2")),
        debtor_city=_first(debtor, "city"),
        debtor_state=_first(debtor, "state"),
        debtor_zip=_first(debtor, "zipcode"),
        secured_party_name=secured_party_name,
        secured_party_normalized=normalize_ucc_name(secured_party_name),
        collateral_description=_collateral_description(collateral),
        filing_date=filing_date,
        termination_date=termination_date,
        status=_status(row, filing_type),
        lender_type="UNKNOWN",
        is_factoring_related=False,
        is_mca_related=False,
        source_state="CO",
        source_url=CO_UCC_SOURCE_URL,
    )


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


def _name(row: dict) -> str | None:
    organization = _first(row, "organizationname", "organizationName")
    if organization:
        return organization
    return _join(_first(row, "firstname"), _first(row, "middlename"), _first(row, "lastname"))


def _join(*parts: str | None) -> str | None:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    return " ".join(cleaned) or None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f", "%m/%d/%Y"):
        try:
            return datetime.strptime(value[:23], fmt).date()
        except ValueError:
            continue
    return None


def _filing_type(row: dict) -> str:
    text = normalize_ucc_name(
        " ".join(
            part
            for part in (
                _first(row, "transactiontype"),
                _first(row, "transactionType"),
                _first(row, "documenttype"),
                _first(row, "documentType"),
                _first(row, "filingtype"),
                _first(row, "filingType"),
            )
            if part
        )
    )
    if (
        _bool(row.get("terminationflag") or row.get("terminationFlag"))
        or "TERMIN" in text
        or "RELEASE" in text
    ):
        return "UCC3"
    if _bool(row.get("continuation")) or "CONTINUATION" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _status(row: dict, filing_type: str) -> str:
    if filing_type == "UCC3" or _bool(
        row.get("terminationflag") or row.get("terminationFlag")
    ):
        return "TERMINATED"
    return "ACTIVE"


def _collateral_description(row: dict) -> str | None:
    return _join(
        _first(row, "collateraldescription"),
        _first(row, "additionalcollateraldescription"),
    )


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _index_related_csv(path: Path) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            fileid = _first(row, "fileid", "fileId")
            if fileid and fileid not in indexed:
                indexed[fileid] = row
    return indexed


def _limited(rows: Iterator[dict], limit: int) -> Iterator[dict]:
    for index, row in enumerate(rows):
        if index >= limit:
            return
        yield row
