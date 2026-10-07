"""Ingest an official Florida Sunbiz CSV, TXT, DAT, or ZIP export."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import httpx
from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.florida_ingest import ingest_fl_file
from porter_verify.db.session import create_db_engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Florida from an official Sunbiz file.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path)
    source.add_argument("--url")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=1_000)
    parser.add_argument("--start-entry", default=None)
    args = parser.parse_args()

    temporary: tempfile.TemporaryDirectory[str] | None = None
    path = args.file
    try:
        if args.url:
            temporary = tempfile.TemporaryDirectory()
            suffix = Path(args.url.lower().split("?")[0]).suffix or ".zip"
            path = Path(temporary.name) / f"florida{suffix}"
            with httpx.stream("GET", args.url, follow_redirects=True, timeout=120) as response:
                response.raise_for_status()
                with path.open("wb") as output:
                    for chunk in response.iter_bytes():
                        output.write(chunk)
        assert path is not None
        factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
        with factory() as session:
            count = ingest_fl_file(
                session,
                path,
                batch_size=args.batch_size,
                limit=args.limit,
                start_entry=args.start_entry,
            )
        print(f"Ingested {count:,} Florida entities.")
    finally:
        if temporary:
            temporary.cleanup()


if __name__ == "__main__":
    main()
