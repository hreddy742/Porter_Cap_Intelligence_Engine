#!/usr/bin/env python3
"""Targeted MN UCC search. Run from repo root:

    python scripts/refresh_mn_ucc.py "ACME CORP"

For debtor-name search, set credentials first:

    export MN_UCC_USERNAME=your@email.com
    export MN_UCC_PASSWORD=yourpassword

To look up by file number (free, no credentials required):

    python scripts/refresh_mn_ucc.py --file-number 123456789

NOTE: MN debtor-name search requires a paid MBLS account ($0.40/search).
      Create an account at https://mblsportal.sos.mn.gov and purchase a
      UCC lookup subscription. Contact ucc.dept@state.mn.us or 651-296-2803.
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.mn_ucc import (
    MnUccAuthRequired,
    MnUccPaywallError,
    search_mn_ucc,
    search_mn_ucc_by_file_number,
)
from porter_verify.db.base import utcnow
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_intelligence import record_refresh_log
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh targeted Minnesota UCC search results."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("company_name", nargs="?", help="Debtor organization name to search")
    group.add_argument(
        "--file-number",
        metavar="FILE_NUMBER",
        help="Look up a single filing by exact MN UCC file number (free, no auth required)",
    )
    args = parser.parse_args()

    started_at = utcnow()
    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    try:
        if args.file_number:
            results = search_mn_ucc_by_file_number(args.file_number)
            search_label = f"file number {args.file_number}"
        else:
            results = search_mn_ucc(args.company_name)
            search_label = args.company_name
    except MnUccAuthRequired as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except MnUccPaywallError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    with factory() as session:
        try:
            count = ingest_public_search_results(session, results)
            record_refresh_log(
                session,
                state="MN",
                refresh_type="TARGETED_SEARCH",
                records_added=count,
                records_updated=0,
                started_at=started_at,
                status="SUCCESS",
            )
        except Exception as exc:
            record_refresh_log(
                session,
                state="MN",
                refresh_type="TARGETED_SEARCH",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise

    print(f"MN UCC: ingested {count:,} result(s) for {search_label!r}.")


if __name__ == "__main__":
    main()
