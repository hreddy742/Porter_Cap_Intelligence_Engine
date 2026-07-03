#!/usr/bin/env python3
"""One-shot NY UCC targeted search refresh for a list of company names.

Run from the repo root:
    python scripts/refresh_ny_ucc.py "Acme Corp" "Widget LLC"

If no company names are passed as arguments the script exits with usage info.
Results are upserted into the local database via the shared
ingest_public_search_results() helper.

Requirements:
    pip install playwright
    playwright install chromium
"""

import sys

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.ny_ucc import search_ny_ucc, to_public_search_results
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main(company_names: list[str]) -> None:
    if not company_names:
        print(
            "Usage: python scripts/refresh_ny_ucc.py <company_name> [<company_name> ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    total = 0
    with factory() as session:
        for name in company_names:
            print(f"Searching NY UCC for: {name!r} ...", flush=True)
            try:
                raw_rows = search_ny_ucc(name)
                public_results = to_public_search_results(name, raw_rows)
                n = ingest_public_search_results(session, public_results)
                print(f"  -> {len(raw_rows)} results found, {n} records upserted")
                total += n
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR searching {name!r}: {exc}", file=sys.stderr)

    print(f"\nNY UCC refresh complete: {total} total records upserted")


if __name__ == "__main__":
    main(sys.argv[1:])
