"""Oregon UCC filing ingestion from official Oregon open-data APIs."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from datetime import date, datetime

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from porter_verify.db.base import utcnow
from porter_verify.db.models import UccFiling
from porter_verify.services.ucc_intelligence import apply_lender_classification, normalize_ucc_name

OR_UCC_MONTHLY_API_URL = "https://data.oregon.gov/resource/snfi-f79b.json"
OR_UCC_MONTHLY_SOURCE_URL = "https://data.oregon.gov/Business/UCC-List-of-Filings-Entered-Last-Month/snfi-f79b"
OR_FARM_PRODUCTS_API_URL = "https://data.oregon.gov/resource/3qaz-7u98.json"
OR_FARM_PRODUCTS_SOURCE_URL = "https://data.oregon.gov/Business/Farm-Products-Master-List/3qaz-7u98"


def fetch_or_ucc_rows(
    *,
    page_size: int = 50_000,
    limit: int | None = None,
    include_farm_products: bool = True,
) -> Iterator[dict]:
    emitted = 0
    for source, url in _source_urls(include_farm_products):
        offset = 0
        with httpx.Client(
            timeout=120, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}
        ) as client:
            while True:
                remaining = None if limit is None else limit - emitted
                if remaining is not None and remaining <= 0:
                    return
                batch_limit = min(page_size, remaining) if remaining is not None else page_size
                response = client.get(
                    url,
                    params={"$limit": batch_limit, "$offset": offset, "$order": "file_number"},
                )
                response.raise_for_status()
                rows = response.json()
                if not rows:
                    break
                for row in rows:
                    row["_source_dataset"] = source
                    yield row
                emitted += len(rows)
                offset += len(rows)


def ingest_or_ucc_rows(
    session: Session,
    rows: Iterable[dict],
    *,
    batch_size: int = 1_000,
) -> int:
    count = 0
    pending: list[dict] = []
    for filing in _filings_from_rows(rows):
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


def _filings_from_rows(rows: Iterable[dict]) -> Iterator[UccFiling]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        source = _first(row, "_source_dataset") or "monthly"
        filing_id = _first(row, "file_number", "lien")
        if not filing_id:
            continue
        groups.setdefault((source, filing_id), []).append(row)

    for (source, filing_id), filing_rows in groups.items():
        filing = _filing_from_group(source, filing_id, filing_rows)
        if filing is not None:
            yield filing


def _filing_from_group(source: str, filing_id: str, rows: list[dict]) -> UccFiling | None:
    debtor = _first_matching(rows, "DB") or rows[0]
    debtor_name = _first(debtor, "entity", "entity_name")
    if not debtor_name:
        return None
    secured_party = _secured_party(rows)
    filing_type = _filing_type(_first(debtor, "file_type", "lien_type"), source)
    filing_date = _parse_date(_first(debtor, "filing_date"))
    termination_date = filing_date if filing_type == "UCC3" else None
    return UccFiling(
        id=f"OR:{source.upper()}:{filing_id}",
        filing_id=filing_id,
        state="OR",
        filing_type=filing_type,
        debtor_name=debtor_name,
        debtor_normalized=normalize_ucc_name(debtor_name),
        debtor_address=_join(
            _first(debtor, "mail_addr_1", "address_1"),
            _first(debtor, "mail_addr_2", "address_2"),
        ),
        debtor_city=_first(debtor, "city_descr", "city"),
        debtor_state=_first(debtor, "st_cd_txt", "state"),
        debtor_zip=_first(debtor, "zip_code_txt", "zip_code"),
        secured_party_name=secured_party,
        secured_party_normalized=normalize_ucc_name(secured_party),
        collateral_description=_collateral(rows, source),
        filing_date=filing_date,
        termination_date=termination_date,
        status=_status(filing_type),
        lender_type="UNKNOWN",
        is_factoring_related=False,
        is_mca_related=False,
        source_state="OR",
        source_url=_source_url(debtor, source),
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


def _source_urls(include_farm_products: bool) -> tuple[tuple[str, str], ...]:
    sources = [("monthly", OR_UCC_MONTHLY_API_URL)]
    if include_farm_products:
        sources.append(("farm_products", OR_FARM_PRODUCTS_API_URL))
    return tuple(sources)


def _first(row: dict, *names: str) -> str | None:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _first_matching(rows: list[dict], party_type: str) -> dict | None:
    for row in rows:
        if (_first(row, "party_type", "entity_type") or "").upper() == party_type:
            return row
    return None


def _secured_party(rows: list[dict]) -> str | None:
    secured = _first_matching(rows, "SP")
    if secured is not None:
        return _first(secured, "entity", "entity_name")
    lookup = _first(rows[0], "secured_party_lookup")
    if not lookup or lookup == "This is a secured party":
        return None
    try:
        parsed = json.loads(lookup)
    except json.JSONDecodeError:
        return lookup
    if isinstance(parsed, list) and parsed:
        return str(parsed[0])
    return lookup


def _collateral(rows: list[dict], source: str) -> str | None:
    if source == "monthly":
        lien_type = _first(rows[0], "lien_type")
        return f"Oregon {lien_type} filing" if lien_type else None
    products = sorted({_first(row, "product") for row in rows if _first(row, "product")})
    county = _first(rows[0], "county")
    crop_year = _first(rows[0], "crop_yr")
    parts = []
    if products:
        parts.append("Products: " + ", ".join(products[:10]))
    if county:
        parts.append(f"County: {county}")
    if crop_year:
        parts.append(f"Crop year: {crop_year}")
    return "; ".join(parts) or None


def _source_url(row: dict, source: str) -> str:
    image_link = row.get("image_link")
    if isinstance(image_link, dict) and image_link.get("url"):
        return str(image_link["url"])
    if source == "farm_products":
        return OR_FARM_PRODUCTS_SOURCE_URL
    return OR_UCC_MONTHLY_SOURCE_URL


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f", "%m/%d/%Y"):
        try:
            return datetime.strptime(value[:23], fmt).date()
        except ValueError:
            continue
    return None


def _filing_type(value: str | None, source: str) -> str:
    if source == "farm_products":
        return "UCC1"
    text = normalize_ucc_name(value)
    if "TERMIN" in text or "RELEASE" in text:
        return "UCC3"
    if "CONTINUATION" in text:
        return "CONTINUATION"
    if "AMEND" in text:
        return "AMENDMENT"
    return "UCC1"


def _status(filing_type: str) -> str:
    if filing_type == "UCC3":
        return "TERMINATED"
    if filing_type == "AMENDMENT":
        return "AMENDED"
    return "ACTIVE"


def _join(*parts: str | None) -> str | None:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    return " ".join(cleaned) or None
