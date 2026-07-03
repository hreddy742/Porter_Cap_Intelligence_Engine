#!/usr/bin/env python3
"""One-shot Maryland UCC targeted search refresh.

Usage (from repo root):
    python scripts/refresh_md_ucc.py "Acme Corp"
    python scripts/refresh_md_ucc.py "Acme Corp" --include-lapsed
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.md_ucc import search_md_ucc, to_public_search_results
from porter_verify.db.base import utcnow
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_intelligence import record_refresh_log
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh targeted Maryland UCC search results."
    )
    parser.add_argument("company_name", help="Debtor name to search")
    args = parser.parse_args()

    started_at = utcnow()
    settings = get_settings()
    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    rows = search_md_ucc(args.company_name)
    results = to_public_search_results(args.company_name, rows)

    with factory() as session:
        try:
            count = ingest_public_search_results(session, results)
            record_refresh_log(
                session,
                state="MD",
                refresh_type="TARGETED_SEARCH",
                records_added=count,
                records_updated=0,
                started_at=started_at,
                status="SUCCESS",
            )
        except Exception as exc:
            record_refresh_log(
                session,
                state="MD",
                refresh_type="TARGETED_SEARCH",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise

    print(f"MD UCC: {count:,} records ingested for '{args.company_name}'.")


if __name__ == "__main__":
    main()
