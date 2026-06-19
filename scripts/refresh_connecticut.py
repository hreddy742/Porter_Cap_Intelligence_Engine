"""Refresh all Connecticut entities from the official Socrata dataset."""

from __future__ import annotations

import argparse

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.connecticut_ingest import ingest_ct_soda
from porter_verify.db.session import create_db_engine


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Development row cap")
    parser.add_argument("--offset", type=int, default=0, help="Resume at a SODA row offset")
    parser.add_argument("--batch-size", type=int, default=1_000)
    args = parser.parse_args()
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        count = ingest_ct_soda(
            session,
            limit=args.limit,
            start_offset=args.offset,
            batch_size=args.batch_size,
        )
    print(f"Ingested {count:,} Connecticut entities.")


if __name__ == "__main__":
    main()
