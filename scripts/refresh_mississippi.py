"""Ingest an official Mississippi Secretary of State CSV or ZIP export."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import httpx
from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.mississippi_ingest import ingest_ms_file
from porter_verify.db.session import create_db_engine


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh Mississippi from an official file. No unverified bulk URL is embedded."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path)
    source.add_argument("--url")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    temporary: tempfile.TemporaryDirectory[str] | None = None
    path = args.file
    try:
        if args.url:
            temporary = tempfile.TemporaryDirectory()
            suffix = ".zip" if args.url.lower().split("?")[0].endswith(".zip") else ".csv"
            path = Path(temporary.name) / f"mississippi{suffix}"
            with httpx.stream("GET", args.url, follow_redirects=True, timeout=120) as response:
                response.raise_for_status()
                with path.open("wb") as output:
                    for chunk in response.iter_bytes():
                        output.write(chunk)
        assert path is not None
        factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
        with factory() as session:
            count = ingest_ms_file(session, path, limit=args.limit)
        print(f"Ingested {count:,} Mississippi entities.")
    finally:
        if temporary:
            temporary.cleanup()


if __name__ == "__main__":
    main()
