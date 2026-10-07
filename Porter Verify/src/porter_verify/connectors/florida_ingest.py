"""Stream Florida Sunbiz CSV, TXT, or ZIP exports into the Florida staging table."""

from __future__ import annotations

import csv
import io
import struct
import zipfile
from collections.abc import Iterator
from pathlib import Path

import inflate64
from sqlalchemy.orm import Session

from porter_verify.connectors.florida import FlBusinessRecord, parse_fl_fixed_width, parse_fl_record
from porter_verify.connectors.staging_upsert import upsert_staging_rows
from porter_verify.db.models import FlBusinessEntity
from porter_verify.logging_config import get_logger
from porter_verify.services.normalization import normalize_name

log = get_logger(__name__)

_DEFLATE64 = 9
_LOCAL_FILE_HEADER = struct.Struct("<IHHHHHIIIHH")


def _text_rows(path: Path) -> Iterator[FlBusinessRecord]:
    with path.open(encoding="utf-8-sig", errors="ignore", newline="") as text:
        if path.suffix.lower() == ".csv":
            yield from (parse_fl_record(row) for row in csv.DictReader(text))
            return
        first = text.readline()
        if first.strip():
            yield parse_fl_fixed_width(first)
        for line in text:
            if line.strip():
                yield parse_fl_fixed_width(line)


def _parse_lines(name: str, lines: Iterator[str]) -> Iterator[FlBusinessRecord]:
    if name.lower().endswith(".csv"):
        yield from (parse_fl_record(row) for row in csv.DictReader(lines))
        return
    for line in lines:
        if line.strip():
            yield parse_fl_fixed_width(line)


def _deflate64_member_chunks(path: Path, info: zipfile.ZipInfo) -> Iterator[bytes]:
    with path.open("rb") as file:
        file.seek(info.header_offset)
        header = file.read(_LOCAL_FILE_HEADER.size)
        signature, *_rest, name_length, extra_length = _LOCAL_FILE_HEADER.unpack(header)
        if signature != 0x04034B50:
            raise ValueError(f"Invalid ZIP local header for {info.filename}")
        file.seek(name_length + extra_length, io.SEEK_CUR)

        inflater = inflate64.Inflater()
        remaining = info.compress_size
        while remaining:
            chunk = file.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            inflated = inflater.inflate(chunk)
            if inflated:
                yield inflated


def _byte_lines(chunks: Iterator[bytes]) -> Iterator[str]:
    pending = b""
    for chunk in chunks:
        pending += chunk
        while b"\n" in pending:
            line, pending = pending.split(b"\n", 1)
            yield line.rstrip(b"\r").decode("cp1252", errors="replace")
    if pending:
        yield pending.rstrip(b"\r").decode("cp1252", errors="replace")


def _rows(path: Path, *, start_entry: str | None = None) -> Iterator[FlBusinessRecord]:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            entries = sorted(
                (
                    info
                    for info in archive.infolist()
                    if info.filename.lower().endswith((".csv", ".txt", ".dat"))
                ),
                key=lambda item: item.filename,
            )
            if start_entry is not None:
                entries = [info for info in entries if info.filename >= start_entry]
            if not entries:
                raise ValueError("Florida ZIP contains no CSV, TXT, or DAT file")
            for info in entries:
                if info.compress_type == _DEFLATE64:
                    yield from _parse_lines(
                        info.filename, _byte_lines(_deflate64_member_chunks(path, info))
                    )
                    continue
                with (
                    archive.open(info) as raw,
                    io.TextIOWrapper(
                        raw, encoding="utf-8-sig", errors="ignore", newline=""
                    ) as text,
                ):
                    yield from _parse_lines(info.filename, text)
        return
    yield from _text_rows(path)


def ingest_fl_file(
    session: Session,
    path: str | Path,
    *,
    batch_size: int = 1_000,
    limit: int | None = None,
    start_entry: str | None = None,
) -> int:
    """Upsert every valid Florida row; returns the number of entities written."""

    count = 0
    pending: list[dict] = []
    for record in _rows(Path(path), start_entry=start_entry):
        if limit is not None and count >= limit:
            break
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
            upsert_staging_rows(session, FlBusinessEntity, pending)
            session.commit()
            pending.clear()
            if count % 50_000 == 0:
                log.info("fl_ingest_progress", rows=count)
    upsert_staging_rows(session, FlBusinessEntity, pending)
    session.commit()
    log.info("fl_ingest_complete", rows=count)
    return count
