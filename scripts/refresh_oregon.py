"""Refresh Oregon active entities from the official Socrata dataset."""

from __future__ import annotations

import argparse

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.oregon_ingest import ingest_or_soda
from porter_verify.db.session import create_db_engine


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--row-limit", type=int, default=None, help="Development raw-row cap")
    args = parser.parse_args()
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        count = ingest_or_soda(session, row_limit=args.row_limit)
    print(f"Ingested {count:,} Oregon active entities.")


if __name__ == "__main__":
    main()
