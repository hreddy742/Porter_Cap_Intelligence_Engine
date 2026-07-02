"""Connecticut UCC filing ingestion from the official data.ct.gov SODA API."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import date, datetime

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from porter_verify.db.base import utcnow
from porter_verify.db.models import UccFiling
from porter_verify.services.ucc_intelligence import apply_lender_classification, normalize_ucc_name

CT_UCC_API_URL = "https://data.ct.gov/resource/xfev-8smz.json"
CT_UCC_SOURCE_URL = "https://data.ct.gov/resource/xfev-8smz"
CT_UCC_FIELDS = (
    "id_lien_flng_nbr",
    "id_ucc_flng_nbr",
    "lien_status",
    "cd_flng_type",
    "tx_lien_descript",
    "debtor_nm_bus",
    "debtor_nm_last",
    "debtor_nm_first",
    "debtor_nm_mid",
    "debtor_ad_str1",
    "debtor_ad_str2",
    "debtor_ad_city",
    "debtor_ad_state",
    "debtor_ad_zip",
    "sec_party_nm_bus",
    "sec_party_nm_last",
    "sec_party_nm_first",
    "sec_party_nm_mid",
    "sec_party_ad_str1",
    "sec_party_ad_city",
    "sec_party_ad_state",
    "sec_party_ad_zip",
    "dt_lapse",
    "dt_accept",
)


def fetch_ct_ucc_rows(*, page_size: int = 50_000, limit: int | None = None) -> Iterator[dict]:
    offset = 0
    emitted = 0
    select_fields = ",".join(CT_UCC_FIELDS)
    with httpx.Client(
        timeout=120, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}
    ) as client:
        while True:
            remaining = None if limit is None else limit - emitted
            if remaining is not None and remaining <= 0:
                return
            batch_limit = min(page_size, remaining) if remaining is not None else page_size
            response = client.get(
                CT_UCC_API_URL,
                params={
                    "$select": select_fields,
                    "$limit": batch_limit,
                    "$offset": offset,
                    "$order": "id_ucc_flng_nbr",
                },
            )
            response.raise_for_status()
            rows = response.json()
            if not rows:
                return
            yield from rows
            emitted += len(rows)
            offset += len(rows)


def ingest_ct_ucc_rows(
    session: Session,
    rows: Iterable[dict],
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


def _filing_from_row(row: dict) -> UccFiling | None:
    filing_id = _first(row, "id_ucc_flng_nbr", "id_lien_flng_nbr")
    debtor_name = _debtor_name(row)
    if not filing_id or not debtor_name:
        return None
    raw_type = _first(row, "cd_flng_type")
    filing_type = _filing_type(raw_type)
    filing_date = _parse_date(_first(row, "dt_accept"))
    termination_date = filing_date if filing_type == "UCC3" else None
    secured_party = _secured_party_name(row)
    return UccFiling(
        id=f"CT:{filing_id}",
        filing_id=filing_id,
        state="CT",
        filing_type=filing_type,
        debtor_name=debtor_name,
        debtor_normalized=normalize_ucc_name(debtor_name),
        debtor_address=_join(_first(row, "debtor_ad_str1"), _first(row, "debtor_ad_str2")),
        debtor_city=_first(row, "debtor_ad_city"),
        debtor_state=_first(row, "debtor_ad_state"),
        debtor_zip=_first(row, "debtor_ad_zip"),
        secured_party_name=secured_party,
        secured_party_normalized=normalize_ucc_name(secured_party),
        collateral_description=_first(row, "tx_lien_descript"),
        filing_date=filing_date,
        termination_date=termination_date,
        status=_status(_first(row, "lien_status"), filing_type),
        lender_type="UNKNOWN",
        is_factoring_related=False,
        is_mca_related=False,
        source_state="CT",
        source_url=CT_UCC_SOURCE_URL,
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


def _debtor_name(row: dict) -> str | None:
    business = _first(row, "debtor_nm_bus")
    if business:
        return business
    return _join(
        _first(row, "debtor_nm_first"),
        _first(row, "debtor_nm_mid"),
        _first(row, "debtor_nm_last"),
    )


def _secured_party_name(row: dict) -> str | None:
    business = _first(row, "sec_party_nm_bus")
    if business:
        return business
    return _join(
        _first(row, "sec_party_nm_first"),
        _first(row, "sec_party_nm_mid"),
        _first(row, "sec_party_nm_last"),
    )


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


def _filing_type(value: str | None) -> str:
    text = normalize_ucc_name(value)
    if "TERMIN" in text or "RELEASE" in text or "DISCHARGE" in text:
        return "UCC3"
    if "CONTINUATION" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _status(value: str | None, filing_type: str) -> str:
    text = normalize_ucc_name(value)
    if filing_type == "UCC3" or "TERMINATED" in text or "RELEASED" in text:
        return "TERMINATED"
    if filing_type == "AMENDMENT":
        return "AMENDED"
    return "ACTIVE"
