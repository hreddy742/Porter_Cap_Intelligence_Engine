#!/usr/bin/env python3
"""One-shot NC UCC targeted search refresh.

NC SOS does not offer a free bulk download.  A paid FTP subscription
($4,000-$5,200/year) is available via [email protected].
Until that contract is in place this script performs targeted searches
for a list of company names and stores the results via the shared
public-search ingestion path.

Run from repo root:
    python scripts/refresh_nc_ucc.py --companies "Acme LLC" "Widget Corp"

Or pipe a newline-delimited file of company names:
    python scripts/refresh_nc_ucc.py --file companies.txt

Requires playwright:
    pip install playwright && playwright install chromium
"""

from __future__ import annotations

import argparse
import sys
import time

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.nc_ucc import search_nc_ucc, to_public_search_results
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_public_search import ingest_public_search_results

_MIN_BETWEEN_COMPANIES_S: float = 6.0  # extra courtesy gap between company searches


def main() -> None:
    parser = argparse.ArgumentParser(description="NC UCC targeted search refresh")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--companies",
        nargs="+",
        metavar="NAME",
        help="One or more company names to search",
    )
    group.add_argument(
        "--file",
        metavar="PATH",
        help="Path to a newline-delimited file of company names",
    )
    args = parser.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            companies = [line.strip() for line in fh if line.strip()]
    else:
        companies = args.companies

    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    total_ingested = 0
    with factory() as session:
        for i, company in enumerate(companies):
            print(f"[{i + 1}/{len(companies)}] Searching NC UCC for: {company!r}")
            try:
                rows = search_nc_ucc(company)
                public = to_public_search_results(company, rows)
                n = ingest_public_search_results(session, public)
                print(f"  -> {len(rows)} result(s), {n} ingested")
                total_ingested += n
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR: {exc}", file=sys.stderr)
            if i < len(companies) - 1:
                time.sleep(_MIN_BETWEEN_COMPANIES_S)

    print(f"\nNC UCC: {total_ingested} total records ingested across {len(companies)} search(es)")


if __name__ == "__main__":
    main()
