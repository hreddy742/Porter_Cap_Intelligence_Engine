#!/usr/bin/env python3
"""One-shot IL UCC targeted search refresh.

Illinois does not offer free bulk UCC data.  Bulk access requires a
$2,500 one-time fee plus $200/week for updates via contract with the
IL Secretary of State.

This script performs targeted searches against the public IL SOS portal
at https://apps.ilsos.gov/uccsearch/ for a list of company names
supplied on the command line (or via stdin, one per line).

Usage:
    # Search a single company
    python scripts/refresh_il_ucc.py "ACME CORPORATION"

    # Search multiple companies
    python scripts/refresh_il_ucc.py "ACME CORP" "BEST BUY" "WALMART INC"

    # Read names from stdin (one per line)
    cat companies.txt | python scripts/refresh_il_ucc.py --stdin

    # Dry-run: print results without writing to DB
    python scripts/refresh_il_ucc.py --dry-run "ACME CORPORATION"

NOTE: The IL SOS portal returns HTTP 403 to some automated requests.
If you see 403 errors, a Playwright-based browser automation approach
will be required.  Contact the IL SOS directly for bulk data access.
"""

import argparse
import sys

sys.path.insert(0, "src")

import httpx
from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.db.session import create_db_engine
from porter_verify.connectors.il_ucc import search_il_ucc, to_public_search_results
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Targeted IL UCC search and ingest for one or more company names."
    )
    parser.add_argument(
        "company_names",
        nargs="*",
        metavar="COMPANY_NAME",
        help="One or more company names to search.",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read company names from stdin (one per line) instead of positional args.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results without writing to the database.",
    )
    args = parser.parse_args()

    if args.stdin:
        company_names = [line.strip() for line in sys.stdin if line.strip()]
    elif args.company_names:
        company_names = args.company_names
    else:
        parser.error("Provide at least one COMPANY_NAME or use --stdin.")
        return  # unreachable, but satisfies type checkers

    if not company_names:
        print("No company names provided. Exiting.", file=sys.stderr)
        sys.exit(1)

    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    total_found = 0
    total_ingested = 0

    for name in company_names:
        print(f"Searching IL UCC for: {name!r} ...", flush=True)
        try:
            raw_rows = search_il_ucc(name)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                print(
                    f"  [WARN] HTTP 403 from IL SOS portal for {name!r}. "
                    "The portal may be blocking automated requests. "
                    "Try using a Playwright-based approach or contact IL SOS for bulk access.",
                    file=sys.stderr,
                )
                continue
            print(f"  [ERROR] HTTP {exc.response.status_code} for {name!r}: {exc}", file=sys.stderr)
            continue
        except httpx.RequestError as exc:
            print(f"  [ERROR] Network error for {name!r}: {exc}", file=sys.stderr)
            continue

        results = to_public_search_results(name, raw_rows)
        total_found += len(results)

        if args.dry_run:
            print(f"  Found {len(results)} filing(s) (dry-run, not ingesting):")
            for r in results:
                print(
                    f"    [{r.status}] {r.filing_id} | {r.debtor_name} "
                    f"| {r.filing_type} | filed {r.filing_date} | confidence {r.match_confidence}"
                )
        else:
            with factory() as session:
                n = ingest_public_search_results(session, results)
            total_ingested += n
            print(f"  Ingested {n} filing(s) for {name!r}.")

    if args.dry_run:
        print(f"\nIL UCC dry-run complete: {total_found} filing(s) found across {len(company_names)} search(es).")
    else:
        print(f"\nIL UCC refresh complete: {total_ingested} record(s) ingested across {len(company_names)} search(es).")


if __name__ == "__main__":
    main()
