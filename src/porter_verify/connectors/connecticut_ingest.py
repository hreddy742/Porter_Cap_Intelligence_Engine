"""Ingest Connecticut business-entity data from the Socrata SODA API.

CT publishes its full registry on data.ct.gov (dataset n7gp-d28j). The SODA
API lets us stream rows as CSV with a simple $limit/$offset pagination pattern.
We upsert into ``ct_business_entities`` keyed by account number. Re-running is
idempotent — existing rows are updated, not duplicated.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from collections.abc import Iterator

from sqlalchemy.orm import Session

from porter_verify.connectors.connecticut import parse_ct_record
from porter_verify.connectors.staging_upsert import upsert_staging_rows
from porter_verify.db.models import CtBusinessEntity
from porter_verify.logging_config import get_logger
from porter_verify.services.normalization import normalize_name

log = get_logger(__name__)

CT_SODA_URL = "https://data.ct.gov/resource/n7gp-d28j.csv"


def _fetch_page(offset: int, page_size: int) -> Iterator[dict]:
    url = f"{CT_SODA_URL}?$limit={page_size}&$offset={offset}&$order=accountnumber"
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        text = resp.read().decode("utf-8", errors="ignore")
    yield from csv.DictReader(io.StringIO(text))


def ingest_ct_soda(
    session: Session,
    *,
    limit: int | None = None,
    batch_size: int = 1_000,
    page_size: int = 10_000,
    start_offset: int = 0,
) -> int:
    """Fetch CT entity rows from SODA and upsert into staging. Returns row count.

    ``limit`` caps total rows (None = all); ``page_size`` controls how many rows
    each SODA request fetches.
    """
    count = 0
    offset = start_offset
    _seen: set[str] = set()
    pending: list[dict] = []

    while True:
        remaining = (limit - count) if limit is not None else page_size
        fetch_n = min(page_size, remaining) if limit is not None else page_size
        rows = list(_fetch_page(offset, fetch_n))
        if not rows:
            break

        for row in rows:
            if limit is not None and count >= limit:
                break
            record = parse_ct_record(row)
            if not record.entity_id or not record.legal_name:
                continue
            if record.entity_id == "0000000":
                continue  # placeholder rows the CT dataset uses for unregistered entities
            if record.entity_id in _seen:
                continue
            _seen.add(record.entity_id)
            pending.append(
                {
                    "entity_id": record.entity_id,
                    "entity_name": record.legal_name,
                    "normalized_name": normalize_name(record.legal_name),
                    "status_raw": record.status_raw,
                    "entity_type": record.entity_type,
                    "formation_date": record.formation_date,
                    "principal_address": record.principal_address,
                    "mailing_address": record.mailing_address,
                    "jurisdiction": record.jurisdiction,
                    "source_record_url": record.source_record_url,
                    "agent_name": None,
                    "agent_address": None,
                    "officers": record.officers,
                    "raw": record.raw,
                }
            )
            count += 1
            if len(pending) >= batch_size:
                upsert_staging_rows(session, CtBusinessEntity, pending)
                session.commit()
                pending.clear()
                log.info("ct_ingest_progress", rows=count)

        offset += len(rows)
        if limit is not None and count >= limit:
            break
        if len(rows) < fetch_n:
            break  # last page

    upsert_staging_rows(session, CtBusinessEntity, pending)
    session.commit()
    log.info("ct_ingest_complete", rows=count)
    return count
