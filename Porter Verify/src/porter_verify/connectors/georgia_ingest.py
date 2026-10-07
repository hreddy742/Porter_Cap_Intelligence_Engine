"""Stream Georgia business CSV or ZIP exports into the Georgia staging table."""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy.orm import Session

from porter_verify.connectors.georgia import parse_ga_record
from porter_verify.connectors.staging_upsert import upsert_staging_rows
from porter_verify.db.models import GaBusinessEntity
from porter_verify.logging_config import get_logger
from porter_verify.services.normalization import normalize_name

log = get_logger(__name__)


def _rows(path: Path) -> Iterator[dict]:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = sorted(name for name in archive.namelist() if name.lower().endswith(".csv"))
            if not names:
                raise ValueError("Georgia ZIP contains no CSV file")
            with (
                archive.open(names[0]) as raw,
                io.TextIOWrapper(raw, encoding="utf-8-sig", errors="ignore", newline="") as text,
            ):
                yield from csv.DictReader(text)
        return
    with path.open(encoding="utf-8-sig", errors="ignore", newline="") as text:
        yield from csv.DictReader(text)


def ingest_ga_file(
    session: Session,
    path: str | Path,
    *,
    batch_size: int = 1_000,
    limit: int | None = None,
) -> int:
    """Upsert every valid Georgia row; returns the number of entities written."""

    count = 0
    pending: list[dict] = []
    for row in _rows(Path(path)):
        if limit is not None and count >= limit:
            break
        record = parse_ga_record(row)
        if not record.entity_id or not record.legal_name:
            continue
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
        count += 1
        if len(pending) >= batch_size:
            upsert_staging_rows(session, GaBusinessEntity, pending)
            session.commit()
            pending.clear()
            log.info("ga_ingest_progress", rows=count)
    upsert_staging_rows(session, GaBusinessEntity, pending)
    session.commit()
    log.info("ga_ingest_complete", rows=count)
    return count
