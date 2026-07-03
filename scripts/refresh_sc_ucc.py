#!/usr/bin/env python3
"""One-shot SC UCC targeted search demo / manual trigger.

Run from repo root:
    python scripts/refresh_sc_ucc.py "ACME TRUCKING LLC"

IMPORTANT: The SC UCC portal at ucconline.sc.gov is a pay-per-search
ASP.NET system ($5 per certified search).  This script is intended for
on-demand, targeted lookups only — NOT bulk ingestion.  Do not run it
in a loop without understanding the potential per-query cost and the
portal's Terms of Service.

For production use, consider the paid bulk-data subscription (~$12,000/yr)
from South Carolina Interactive LLC:
    1301 Gervais Street Suite 710, Columbia SC 29201
"""

import sys

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.sc_ucc import search_sc_ucc, to_public_search_results
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main(company_name: str) -> None:
    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    print(f"Searching SC UCC for: {company_name!r}")
    raw_rows = search_sc_ucc(company_name)
    print(f"  Found {len(raw_rows)} raw result(s) from the portal.")

    results = to_public_search_results(company_name, raw_rows)

    with factory() as session:
        n = ingest_public_search_results(session, results)

    print(f"SC UCC: {n} record(s) ingested for query {company_name!r}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/refresh_sc_ucc.py <company_name>")
        print('Example: python scripts/refresh_sc_ucc.py "WALMART INC"')
        sys.exit(1)
    main(" ".join(sys.argv[1:]))
