#!/usr/bin/env python3
"""One-shot NV UCC targeted search refresh.

Run from repo root::

    python scripts/refresh_nv_ucc.py "Company Name"

Nevada's UCC search entry points are bot-management blocked (confirmed
live 2026-07-02): nvsos.gov returns an Akamai "Access Denied" page, and
esos.nv.gov returns an Incapsula bot-management challenge. Running this
script will therefore currently always fail with an `NvUccBlockedError`.
It is kept as a placeholder entry point so that once Porter Verify has a
browser-fingerprint-evasion or anti-bot bypass solution, or a bulk/data-
licensing arrangement with the NV SOS, `porter_verify.connectors.nv_ucc`
can be updated to actually fetch and ingest results.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.nv_ucc import (
    NvUccBlockedError,
    search_nv_ucc,
    to_public_search_results,
)
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: python scripts/refresh_nv_ucc.py <company_name>",
            file=sys.stderr,
        )
        print(
            "Example: python scripts/refresh_nv_ucc.py \"Acme LLC\"",
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

    print(f"NV UCC: searching for '{company_name}' ...")
    try:
        raw_rows = search_nv_ucc(company_name)
    except NvUccBlockedError as exc:
        print(f"NV UCC: blocked -- {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"NV UCC: search failed -- {exc}", file=sys.stderr)
        return 3

    print(f"NV UCC: {len(raw_rows)} raw result(s) returned.")
    results = to_public_search_results(company_name, raw_rows)

    with factory() as session:
        n = ingest_public_search_results(session, results)

    print(f"NV UCC: {n} record(s) ingested for '{company_name}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
