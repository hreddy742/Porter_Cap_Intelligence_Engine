"""Ingest Oregon business-entity data from the Socrata SODA API.

Oregon's SODA dataset (tckn-sxa6) uses a long format — multiple rows per entity.
We fetch pages, group by registry_number, pivot with ``pivot_or_rows``, then
upsert one row per entity into ``or_business_entities``. Re-running is idempotent.

Because OR only publishes active entities, we fetch all rows up to the limit.
The pivot step discards any group that has no PRINCIPAL PLACE OF BUSINESS row.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from collections.abc import Iterator

from sqlalchemy.orm import Session

from porter_verify.connectors.oregon import pivot_or_rows
from porter_verify.connectors.staging_upsert import upsert_staging_rows
from porter_verify.db.models import OrBusinessEntity
from porter_verify.logging_config import get_logger
from porter_verify.services.normalization import normalize_name

log = get_logger(__name__)

OR_SODA_URL = "https://data.oregon.gov/resource/tckn-sxa6.csv"


def _fetch_page(offset: int, page_size: int) -> list[dict]:
    url = (
        f"{OR_SODA_URL}?$limit={page_size}&$offset={offset}"
        "&$order=registry_number,associated_name_type"
    )
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        text = resp.read().decode("utf-8", errors="ignore")
    return list(csv.DictReader(io.StringIO(text)))


def ingest_or_soda(
    session: Session,
    *,
    row_limit: int | None = None,
    batch_size: int = 500,
    page_size: int = 10_000,
) -> int:
    """Fetch OR long-format rows from SODA, pivot, and upsert into staging.

    Returns the number of entities written (not raw rows fetched).

    ``row_limit`` caps raw rows fetched (not entities); ~4 raw rows per entity
    means row_limit=40_000 yields ~10_000 entities.
    """

    def pages() -> Iterator[dict]:
        offset = 0
        fetched = 0
        while row_limit is None or fetched < row_limit:
            fetch_n = page_size if row_limit is None else min(page_size, row_limit - fetched)
            page = _fetch_page(offset, fetch_n)
            if not page:
                return
            yield from page
            fetched += len(page)
            offset += len(page)
            log.info("or_ingest_fetch", raw_rows=fetched)
            if len(page) < fetch_n:
                return

    pending: list[dict] = []

    def stage(rows: list[dict]) -> bool:
        record = pivot_or_rows(rows)
        if record is None:
            return False
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
                "agent_name": record.agent_name,
                "agent_address": record.agent_address,
                "officers": record.officers,
                "raw": record.raw,
            }
        )
        return True

    # The ordered stream keeps one entity group in memory and carries it across
    # API page boundaries, so a large full refresh has flat memory usage.
    count = 0
    current_key: str | None = None
    current_rows: list[dict] = []
    for row in pages():
        key = (row.get("registry_number") or "").strip()
        if not key:
            continue
        if current_key is not None and key != current_key:
            count += int(stage(current_rows))
            if len(pending) >= batch_size:
                upsert_staging_rows(session, OrBusinessEntity, pending)
                session.commit()
                pending.clear()
                log.info("or_ingest_progress", entities=count)
            current_rows = []
        current_key = key
        current_rows.append(row)
    if current_rows:
        count += int(stage(current_rows))

    upsert_staging_rows(session, OrBusinessEntity, pending)
    session.commit()
    log.info("or_ingest_complete", entities=count)
    return count
