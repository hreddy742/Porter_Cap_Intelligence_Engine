#!/usr/bin/env python3
"""One-shot KY UCC targeted search refresh.

Kentucky does not offer a free bulk UCC data download — the Bulk Data
Service requires a Kentucky.gov OIDC login and a $1,500/month commercial
subscription.  This script therefore runs a targeted search for a list of
company names and ingests the results via the public search connector.

Run from repo root:
    python scripts/refresh_ky_ucc.py "COMPANY NAME" ["SECOND COMPANY" ...]

If no names are supplied the script reads newline-delimited names from stdin.

Example:
    python scripts/refresh_ky_ucc.py "ACME CORP" "BLUEGRASS LOGISTICS LLC"
    echo -e "ACME CORP\nBLUEGRASS LLC" | python scripts/refresh_ky_ucc.py
"""
import sys

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.ky_ucc import search_ky_ucc, to_public_search_results
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main() -> None:
    # Collect company names from CLI args or stdin
    if len(sys.argv) > 1:
        company_names = [name.strip() for name in sys.argv[1:] if name.strip()]
    else:
        company_names = [line.strip() for line in sys.stdin if line.strip()]

    if not company_names:
        print(
            "Usage: python scripts/refresh_ky_ucc.py \"COMPANY NAME\" [\"SECOND\" ...]\n"
            "       echo \"COMPANY NAME\" | python scripts/refresh_ky_ucc.py",
            file=sys.stderr,
        )
        sys.exit(1)

    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    total = 0
    with factory() as session:
        for company_name in company_names:
            print(f"KY UCC: searching for '{company_name}' ...", flush=True)
            try:
                raw_rows = search_ky_ucc(company_name)
                results = to_public_search_results(company_name, raw_rows)
                n = ingest_public_search_results(session, results)
                print(f"  -> {n} record(s) ingested")
                total += n
            except Exception as exc:
                print(f"  ERROR: {exc}", file=sys.stderr)

    print(f"\nKY UCC: {total} total record(s) ingested across {len(company_names)} search(es).")


if __name__ == "__main__":
    main()
