#!/usr/bin/env python3
"""One-shot AR UCC targeted search refresh.

Run from repo root::

    python scripts/refresh_ar_ucc.py "Company Name"

Arkansas has no free bulk UCC dataset, but the free public debtor-name
search at bcs.sos.arkansas.gov/search/ucc works without any bot-management
block (confirmed live 2026-07-02). This script performs a real search and
ingests the results.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.ar_ucc import search_ar_ucc, to_public_search_results
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: python scripts/refresh_ar_ucc.py <company_name>",
            file=sys.stderr,
        )
        print(
            "Example: python scripts/refresh_ar_ucc.py \"Acme LLC\"",
            file=sys.stderr,
        )
        return 1

    company_name = " ".join(argv[1:]).strip()
    if not company_name:
        print("Error: company_name must not be empty.", file=sys.stderr)
        return 1

    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    print(f"AR UCC: searching for '{company_name}' ...")
    try:
        raw_rows = search_ar_ucc(company_name)
    except Exception as exc:  # noqa: BLE001
        print(f"AR UCC: search failed -- {exc}", file=sys.stderr)
        return 3

    print(f"AR UCC: {len(raw_rows)} raw result(s) returned.")
    results = to_public_search_results(company_name, raw_rows)

    with factory() as session:
        n = ingest_public_search_results(session, results)

    print(f"AR UCC: {n} record(s) ingested for '{company_name}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
