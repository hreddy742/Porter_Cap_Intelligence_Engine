#!/usr/bin/env python3
"""One-shot PA UCC targeted search refresh.

Pennsylvania does not provide a bulk UCC download.  This script is designed
to be called per-company (e.g. from the UCC manual queue) rather than as a
full-state bulk ingest.

Usage
-----
Single company lookup (prints results to stdout):
    python scripts/refresh_pa_ucc.py "ACME CORP"

Ingest results for a single company into the database:
    python scripts/refresh_pa_ucc.py "ACME CORP" --ingest

Include lapsed/terminated filings:
    python scripts/refresh_pa_ucc.py "ACME CORP" --ingest --include-lapsed
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "src")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PA UCC targeted search refresh",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "company_name",
        nargs="?",
        default=None,
        help="Organisation debtor name to search (required unless --help)",
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        default=False,
        help="Write results to the database (default: dry-run, print only)",
    )
    parser.add_argument(
        "--include-lapsed",
        action="store_true",
        default=False,
        help="Include lapsed/terminated filings in the search",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if not args.company_name:
        print("ERROR: company_name is required.", file=sys.stderr)
        print("Usage: python scripts/refresh_pa_ucc.py \"COMPANY NAME\" [--ingest]", file=sys.stderr)
        sys.exit(1)

    company_name: str = args.company_name.strip()

    from porter_verify.connectors.pa_ucc import search_pa_ucc, to_public_search_results

    print(f"PA UCC: searching for {company_name!r} ...")
    rows = search_pa_ucc(company_name, include_lapsed=args.include_lapsed)
    results = to_public_search_results(company_name, rows)

    print(f"PA UCC: {len(results)} filing(s) found")
    for r in results:
        print(
            f"  [{r.status}] {r.filing_id}  debtor={r.debtor_name!r}"
            f"  sp={r.secured_party_name!r}  filed={r.filing_date}"
            f"  confidence={r.match_confidence}"
        )

    if not args.ingest:
        print("(dry-run: pass --ingest to write to database)")
        return

    from sqlalchemy.orm import sessionmaker

    from porter_verify.config import get_settings
    from porter_verify.db.session import create_db_engine
    from porter_verify.services.ucc_public_search import ingest_public_search_results

    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as session:
        n = ingest_public_search_results(session, results)

    print(f"PA UCC: {n} record(s) ingested for {company_name!r}")


if __name__ == "__main__":
    main()
