#!/usr/bin/env python3
"""One-shot MO UCC targeted search refresh.

Run from repo root::

    python scripts/refresh_mo_ucc.py "Company Name"

Missouri does not offer a bulk UCC data download and, unlike states such
as NJ or KY, does not expose a free-form public search either -- the SOS
UCC portal at bsd.sos.mo.gov requires a registered Corporate E-account
(ACH-backed, ~7 business day setup) before any debtor-name search can be
performed.

Running this script will therefore currently always fail with a
`MissouriUccAuthRequiredError` explaining what is required. It is kept
as a placeholder entry point so that once Porter Verify has:

  * a provisioned Corporate E-account, or
  * a bulk/data-licensing arrangement with the MO SOS UCC Division
    (573-751-4628 or 866-223-6535 opt 4)

...this script and `porter_verify.connectors.mo_ucc` can be updated
(with a real authenticated Selenium/Playwright session) to actually
fetch and ingest results.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "src")

from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.mo_ucc import (
    MissouriUccAuthRequiredError,
    search_mo_ucc,
    to_public_search_results,
)
from porter_verify.db.session import create_db_engine
from porter_verify.services.ucc_public_search import ingest_public_search_results


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: python scripts/refresh_mo_ucc.py <company_name>",
            file=sys.stderr,
        )
        print(
            "Example: python scripts/refresh_mo_ucc.py \"Acme LLC\"",
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

    print(f"MO UCC: searching for '{company_name}' ...")
    try:
        raw_rows = search_mo_ucc(company_name)
    except MissouriUccAuthRequiredError as exc:
        print(f"MO UCC: authentication required -- {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"MO UCC: search failed -- {exc}", file=sys.stderr)
        return 3

    print(f"MO UCC: {len(raw_rows)} raw result(s) returned.")
    results = to_public_search_results(company_name, raw_rows)

    with factory() as session:
        n = ingest_public_search_results(session, results)

    print(f"MO UCC: {n} record(s) ingested for '{company_name}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
