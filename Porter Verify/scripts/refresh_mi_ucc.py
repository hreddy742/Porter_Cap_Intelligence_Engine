#!/usr/bin/env python3
"""One-shot MI UCC targeted-search refresh.

This script is NOT a bulk ingest — Michigan does not offer a publicly
accessible bulk UCC dataset.  Instead it re-runs targeted searches for
any company names already stored in the database as MI UCC search queries
so that their match confidence and status stay current.

Run from the repo root:
    python scripts/refresh_mi_ucc.py [--company "ACME LLC"] [--lapsed]

Options:
    --company NAME   Search for a specific company name (can be repeated).
    --lapsed         Include lapsed/expired filings in results.
    --help           Show this help message.

Without --company the script replays all distinct search_query values that
are already stored in ucc_filings for state='MI', refreshing their records.
If no prior MI queries exist in the database the script exits cleanly with
no records written.
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "src")

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.mi_ucc import search_mi_ucc, to_public_search_results
from porter_verify.db.models import UccFiling
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_public_search import ingest_public_search_results


def _collect_queries(session: Session, extra: list[str]) -> list[str]:
    """Return deduplicated search queries to run."""
    seen: set[str] = set()
    queries: list[str] = []

    # Pull previously stored MI search queries from the database
    rows = session.execute(
        select(UccFiling.search_query)
        .where(UccFiling.state == "MI")
        .where(UccFiling.search_query.isnot(None))
        .distinct()
    ).scalars().all()
    for q in rows:
        key = q.strip()
        if key and key not in seen:
            queries.append(key)
            seen.add(key)

    # Add any names passed on the command line
    for name in extra:
        key = name.strip()
        if key and key not in seen:
            queries.append(key)
            seen.add(key)

    return queries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--company",
        dest="companies",
        action="append",
        default=[],
        metavar="NAME",
        help="Company name to search (may be repeated)",
    )
    parser.add_argument(
        "--lapsed",
        action="store_true",
        default=False,
        help="Include lapsed filings",
    )
    args = parser.parse_args()

    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as session:
        queries = _collect_queries(session, args.companies)

        if not queries:
            print(
                "MI UCC: no search queries found. "
                "Pass --company 'Name' to search for a specific company."
            )
            return

        total = 0
        for company_name in queries:
            print(f"MI UCC: searching for '{company_name}' …", end=" ", flush=True)
            try:
                raw_rows = search_mi_ucc(company_name, include_lapsed=args.lapsed)
                results = to_public_search_results(company_name, raw_rows)
                n = ingest_public_search_results(session, results)
                print(f"{n} records upserted")
                total += n
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR: {exc}")

        print(f"MI UCC: {total} total records ingested across {len(queries)} queries")


if __name__ == "__main__":
    main()
