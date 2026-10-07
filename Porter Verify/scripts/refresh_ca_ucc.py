#!/usr/bin/env python3
"""One-shot CA UCC targeted search refresh for a list of company names.

CA does not expose a public bulk UCC dataset — bulk downloads require an
authenticated, paid SOS account.  This script drives a Playwright headless
browser against the public BizFile SPA to search each company name and
ingest results into the local database.

Usage (from repo root):
  python scripts/refresh_ca_ucc.py "Company Name One" "Company Name Two"

If no names are supplied on the command line the script exits with a usage
message.

Prerequisites:
  pip install playwright
  playwright install chromium
"""

from __future__ import annotations

import sys

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.ca_ucc import search_ca_ucc, to_public_search_results
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main(company_names: list[str]) -> None:
    if not company_names:
        print(
            "Usage: python scripts/refresh_ca_ucc.py \"Company Name\" [\"Another Name\" ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    total_ingested = 0
    with factory() as session:
        for name in company_names:
            print(f"CA UCC: searching for '{name}' ...", flush=True)
            try:
                raw_rows = search_ca_ucc(name)
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR searching '{name}': {exc}", file=sys.stderr)
                continue
            results = to_public_search_results(name, raw_rows)
            if not results:
                print(f"  No results for '{name}'")
                continue
            n = ingest_public_search_results(session, results)
            print(f"  Ingested {n} record(s) for '{name}'")
            total_ingested += n

    print(f"\nCA UCC: {total_ingested} total records ingested")


if __name__ == "__main__":
    main(sys.argv[1:])
