"""Refresh Colorado UCC filings from official data.colorado.gov datasets."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.colorado_ucc import (
    fetch_co_ucc_rows,
    ingest_co_ucc_csv_dir,
    ingest_co_ucc_rows,
)
from porter_verify.db.base import utcnow
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_intelligence import detect_exit_signals, record_refresh_log


def refresh_co_ucc(
    *,
    csv_dir: Path | None = None,
    limit: int | None = None,
    page_size: int = 50_000,
) -> tuple[int, int]:
    started_at = utcnow()
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        try:
            if csv_dir is not None:
                count = ingest_co_ucc_csv_dir(session, csv_dir, limit=limit)
            else:
                rows = fetch_co_ucc_rows(page_size=page_size, limit=limit)
                count = ingest_co_ucc_rows(session, rows)
            exits = detect_exit_signals(session)
            record_refresh_log(
                session,
                state="CO",
                refresh_type="FULL",
                records_added=count,
                records_updated=0,
                started_at=started_at,
                status="SUCCESS",
            )
            return count, exits
        except Exception as exc:
            record_refresh_log(
                session,
                state="CO",
                refresh_type="FULL",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Colorado UCC filings.")
    parser.add_argument("--csv-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--page-size", type=int, default=50_000)
    args = parser.parse_args()

    count, exits = refresh_co_ucc(
        csv_dir=args.csv_dir,
        limit=args.limit,
        page_size=args.page_size,
    )
    print(f"Ingested {count:,} Colorado UCC filings. Exit signals detected: {exits:,}.")


if __name__ == "__main__":
    main()
