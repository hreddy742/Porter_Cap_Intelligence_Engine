"""Refresh Florida UCC filings from Florida Secured Transaction Registry downloads."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.florida_ucc import download_fl_ucc_zips, ingest_fl_ucc_zip_dir
from porter_verify.db.base import utcnow
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_intelligence import detect_exit_signals, record_refresh_log


def refresh_fl_ucc(
    *,
    zip_dir: Path,
    download: bool = False,
    limit: int | None = None,
) -> tuple[int, int]:
    started_at = utcnow()
    if download:
        download_fl_ucc_zips(zip_dir)
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        try:
            count = ingest_fl_ucc_zip_dir(session, zip_dir, limit=limit)
            exits = detect_exit_signals(session)
            record_refresh_log(
                session,
                state="FL",
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
                state="FL",
                refresh_type="FULL",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Florida UCC filings.")
    parser.add_argument("--zip-dir", type=Path, default=Path("data/florida_ucc"))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    count, exits = refresh_fl_ucc(zip_dir=args.zip_dir, download=args.download, limit=args.limit)
    print(f"Ingested {count:,} Florida UCC filings. Exit signals detected: {exits:,}.")


if __name__ == "__main__":
    main()
