"""Refresh Oregon UCC filings from official Oregon open-data APIs."""

from __future__ import annotations

import argparse

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.oregon_ucc import fetch_or_ucc_rows, ingest_or_ucc_rows
from porter_verify.db.base import utcnow
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_intelligence import detect_exit_signals, record_refresh_log


def refresh_or_ucc(
    *,
    limit: int | None = None,
    page_size: int = 50_000,
    include_farm_products: bool = True,
) -> tuple[int, int]:
    started_at = utcnow()
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        try:
            rows = fetch_or_ucc_rows(
                page_size=page_size,
                limit=limit,
                include_farm_products=include_farm_products,
            )
            count = ingest_or_ucc_rows(session, rows)
            exits = detect_exit_signals(session)
            record_refresh_log(
                session,
                state="OR",
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
                state="OR",
                refresh_type="FULL",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Oregon UCC filings.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--page-size", type=int, default=50_000)
    parser.add_argument(
        "--monthly-only",
        action="store_true",
        help="Only ingest the Oregon UCC list of filings entered last month.",
    )
    args = parser.parse_args()

    count, exits = refresh_or_ucc(
        limit=args.limit,
        page_size=args.page_size,
        include_farm_products=not args.monthly_only,
    )
    print(f"Ingested {count:,} Oregon UCC filings. Exit signals detected: {exits:,}.")


if __name__ == "__main__":
    main()
