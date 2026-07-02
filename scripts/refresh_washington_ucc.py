"""Refresh Washington UCC filings from an official CSV/JSON file or URL."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import httpx
from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.washington_ucc import ingest_washington_ucc_file
from porter_verify.db.base import utcnow
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_intelligence import detect_exit_signals, record_refresh_log


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Washington UCC filings.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path)
    source.add_argument("--url")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=1_000)
    args = parser.parse_args()

    temporary: tempfile.TemporaryDirectory[str] | None = None
    path = args.file
    started_at = utcnow()
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        try:
            if args.url:
                temporary = tempfile.TemporaryDirectory()
                suffix = Path(args.url.lower().split("?")[0]).suffix or ".csv"
                path = Path(temporary.name) / f"washington_ucc{suffix}"
                with httpx.stream("GET", args.url, follow_redirects=True, timeout=120) as response:
                    response.raise_for_status()
                    with path.open("wb") as output:
                        for chunk in response.iter_bytes():
                            output.write(chunk)
            assert path is not None
            count = ingest_washington_ucc_file(
                session, path, batch_size=args.batch_size, limit=args.limit
            )
            detect_exit_signals(session)
            record_refresh_log(
                session,
                state="WA",
                refresh_type="FULL",
                records_added=count,
                records_updated=0,
                started_at=started_at,
                status="SUCCESS",
            )
            print(f"Ingested {count:,} Washington UCC filings.")
        except Exception as exc:
            record_refresh_log(
                session,
                state="WA",
                refresh_type="FULL",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise
        finally:
            if temporary:
                temporary.cleanup()


if __name__ == "__main__":
    main()
