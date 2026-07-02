"""Run a targeted New Jersey public UCC search and ingest results."""

from __future__ import annotations

import argparse

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.new_jersey_ucc import search_new_jersey_ucc, to_public_search_results
from porter_verify.db.base import utcnow
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_intelligence import record_refresh_log
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh targeted New Jersey UCC search results.")
    parser.add_argument("company_name")
    parser.add_argument("--include-lapsed", action="store_true")
    args = parser.parse_args()

    started_at = utcnow()
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    rows = search_new_jersey_ucc(args.company_name, include_lapsed=args.include_lapsed)
    results = to_public_search_results(args.company_name, rows)
    with factory() as session:
        try:
            count = ingest_public_search_results(session, results)
            record_refresh_log(
                session,
                state="NJ",
                refresh_type="TARGETED_SEARCH",
                records_added=count,
                records_updated=0,
                started_at=started_at,
                status="SUCCESS",
            )
        except Exception as exc:
            record_refresh_log(
                session,
                state="NJ",
                refresh_type="TARGETED_SEARCH",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise
    print(f"Ingested {count:,} New Jersey public-search UCC results.")


if __name__ == "__main__":
    main()
