"""Download the Colorado business-entity bulk dataset and ingest it.

This is the "no API, no scraping" data path: Colorado publishes the full dataset as
a downloadable CSV. We stream it to disk, then ingest into the staging table the
Colorado connector reads.

Usage:
    python scripts/refresh_colorado.py            # full dataset (large, slow)
    PORTER_CO_INGEST_LIMIT=5000 python scripts/refresh_colorado.py   # dev/demo sample

The bulk export URL is the dataset's CSV download (not the query API).
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.colorado_ingest import ingest_co_csv
from porter_verify.db.session import create_db_engine

# Bulk CSV export of dataset 4ykn-tg5h (a file download, not the query API).
CO_BULK_CSV_URL = "https://data.colorado.gov/api/views/4ykn-tg5h/rows.csv?accessType=DOWNLOAD"


def main() -> None:
    settings = get_settings()
    limit = (
        int(os.environ["PORTER_CO_INGEST_LIMIT"])
        if "PORTER_CO_INGEST_LIMIT" in os.environ
        else None
    )

    dest = Path("./data/colorado_business.csv")
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading Colorado dataset to {dest} ...")
    with httpx.stream("GET", CO_BULK_CSV_URL, follow_redirects=True, timeout=120) as resp:
        resp.raise_for_status()
        with dest.open("wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    print(f"Downloaded {dest.stat().st_size:,} bytes.")

    engine = create_db_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        count = ingest_co_csv(session, dest, limit=limit)
    print(f"Ingested {count:,} Colorado entities" + (f" (limit {limit})" if limit else "") + ".")


if __name__ == "__main__":
    main()
