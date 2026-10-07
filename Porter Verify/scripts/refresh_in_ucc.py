#!/usr/bin/env python3
"""One-shot IN UCC targeted search refresh.

Run from repo root::

    python scripts/refresh_in_ucc.py "Company Name"

Indiana's free public UCC search at bsd.sos.in.gov/PublicUCCSearch requires
solving a CAPTCHA before returning results (confirmed live 2026-07-02).
Running this script will therefore currently always fail with an
`InUccCaptchaRequiredError`. It is kept as a placeholder entry point so
that once Porter Verify has a CAPTCHA-solving integration or a manual
session-cookie workflow, `porter_verify.connectors.in_ucc` can be updated
to actually fetch and ingest results.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.in_ucc import (
    InUccCaptchaRequiredError,
    search_in_ucc,
    to_public_search_results,
)
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: python scripts/refresh_in_ucc.py <company_name>",
            file=sys.stderr,
        )
        print(
            "Example: python scripts/refresh_in_ucc.py \"Acme LLC\"",
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

    print(f"IN UCC: searching for '{company_name}' ...")
    try:
        raw_rows = search_in_ucc(company_name)
    except InUccCaptchaRequiredError as exc:
        print(f"IN UCC: CAPTCHA required -- {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"IN UCC: search failed -- {exc}", file=sys.stderr)
        return 3

    print(f"IN UCC: {len(raw_rows)} raw result(s) returned.")
    results = to_public_search_results(company_name, raw_rows)

    with factory() as session:
        n = ingest_public_search_results(session, results)

    print(f"IN UCC: {n} record(s) ingested for '{company_name}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
