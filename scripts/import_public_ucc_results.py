"""Import targeted public-search UCC results from a normalized CSV."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_public_search import (
    PublicSearchUccResult,
    ingest_public_search_results,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import public-search UCC result CSV.")
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()

    results = [_result_from_row(row) for row in _rows(args.csv_path)]
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        count = ingest_public_search_results(session, results)
    print(f"Imported {count:,} public-search UCC results.")


def _rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _result_from_row(row: dict) -> PublicSearchUccResult:
    return PublicSearchUccResult(
        state=_required(row, "state"),
        filing_id=_required(row, "filing_id"),
        debtor_name=_required(row, "debtor_name"),
        filing_type=_required(row, "filing_type"),
        status=row.get("status") or "ACTIVE",
        search_query=row.get("search_query") or _required(row, "debtor_name"),
        source_url=row.get("source_url") or "",
        secured_party_name=row.get("secured_party_name") or None,
        filing_date=_parse_date(row.get("filing_date")),
        termination_date=_parse_date(row.get("termination_date")),
        collateral_description=row.get("collateral_description") or None,
        debtor_address=row.get("debtor_address") or None,
        debtor_city=row.get("debtor_city") or None,
        debtor_state=row.get("debtor_state") or None,
        debtor_zip=row.get("debtor_zip") or None,
        match_confidence=_parse_int(row.get("match_confidence")),
    )


def _required(row: dict, name: str) -> str:
    value = row.get(name)
    if value is None or not value.strip():
        raise ValueError(f"Missing required column value: {name}")
    return value.strip()


def _parse_date(value: str | None):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {value}")


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    return int(value)


if __name__ == "__main__":
    main()
