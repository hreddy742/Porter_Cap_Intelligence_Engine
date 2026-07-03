#!/usr/bin/env python3
"""Targeted Wisconsin UCC public-search refresh.

Run from repo root::

    python scripts/refresh_wi_ucc.py "Acme Corp"
    python scripts/refresh_wi_ucc.py "Acme Corp" --include-lapsed
    python scripts/refresh_wi_ucc.py "Acme Corp" --search-logic "Starts With"

Prerequisites::

    pip install playwright
    playwright install chromium

Wisconsin UCC data lives in a JavaScript single-page application at
https://wims.dfi.wi.gov/uccsearch — plain HTTP scraping will not work.
Playwright is required to drive the browser and retrieve results.

For bulk (all-Wisconsin) ingestion contact DFI-UCC@dfi.wisconsin.gov or
call (608) 266-8915 to purchase the weekly data file subscription
($250/file or $500/month).
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.wi_ucc import search_wi_ucc, to_public_search_results
from porter_verify.db.base import utcnow
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_intelligence import record_refresh_log
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh targeted Wisconsin UCC search results.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("company_name", help="Business name to search")
    parser.add_argument(
        "--include-lapsed",
        action="store_true",
        help="Include lapsed and terminated filings (default: active only)",
    )
    parser.add_argument(
        "--search-logic",
        default="Exact Match",
        choices=["Starts With", "Contains", "Exact Match", "Standard Search Logic"],
        help="Search logic to use on the WIMS portal",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show the browser window (useful for debugging)",
    )
    args = parser.parse_args()

    started_at = utcnow()
    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    try:
        rows = search_wi_ucc(
            args.company_name,
            search_logic=args.search_logic,
            include_lapsed=args.include_lapsed,
            headless=not args.no_headless,
        )
    except ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    results = to_public_search_results(args.company_name, rows)

    with factory() as session:
        try:
            count = ingest_public_search_results(session, results)
            record_refresh_log(
                session,
                state="WI",
                refresh_type="TARGETED_SEARCH",
                records_added=count,
                records_updated=0,
                started_at=started_at,
                status="SUCCESS",
            )
        except Exception as exc:
            record_refresh_log(
                session,
                state="WI",
                refresh_type="TARGETED_SEARCH",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise

    print(f"WI UCC: {count:,} records ingested for '{args.company_name}'.")


if __name__ == "__main__":
    main()
