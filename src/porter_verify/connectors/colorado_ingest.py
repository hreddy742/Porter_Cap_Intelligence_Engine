"""Ingest the Colorado bulk CSV into the staging table.

Streams the file row-by-row (the full dataset is large), parses each row with the
pure functions in ``colorado.py``, and upserts into ``co_business_entities`` keyed
by the state's entity id. Re-running is idempotent — existing rows are updated, not
duplicated. Commits in batches to keep memory flat.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy.orm import Session

from porter_verify.connectors.colorado import parse_record
from porter_verify.db.models import CoBusinessEntity
from porter_verify.logging_config import get_logger
from porter_verify.services.normalization import normalize_name

log = get_logger(__name__)


def _rows(path: Path) -> Iterator[dict]:
    """Yield CSV rows as dicts (streamed, not loaded all at once)."""

    with path.open(encoding="utf-8", errors="ignore", newline="") as f:
        yield from csv.DictReader(f)


def ingest_co_csv(
    session: Session,
    path: str | Path,
    *,
    batch_size: int = 1000,
    limit: int | None = None,
) -> int:
    """Upsert rows from the Colorado CSV at ``path``. Returns the row count.

    Rows without an entity id or name are skipped (can't be keyed or searched).
    ``limit`` caps how many valid rows to ingest (useful for dev/demo seeding of the
    very large full dataset); ``None`` ingests everything.
    """

    path = Path(path)
    count = 0
    for row in _rows(path):
        if limit is not None and count >= limit:
            break
        record = parse_record(row)
        if not record.entity_id or not record.legal_name:
            continue
        session.merge(
            CoBusinessEntity(
                entity_id=record.entity_id,
                entity_name=record.legal_name,
                normalized_name=normalize_name(record.legal_name),
                status_raw=record.status_raw,
                entity_type=record.entity_type,
                formation_date=record.formation_date,
                principal_address=record.principal_address,
                agent_name=record.agent_name,
                agent_address=record.agent_address,
                raw=record.raw,
            )
        )
        count += 1
        if count % batch_size == 0:
            session.commit()
            log.info("co_ingest_progress", rows=count)
    session.commit()
    log.info("co_ingest_complete", rows=count)
    return count
