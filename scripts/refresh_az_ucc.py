#!/usr/bin/env python3
"""One-shot AZ UCC targeted-search refresh.

This script is intentionally a no-op bulk ingest because Arizona UCC data
is only available as a paid bulk product.  It serves as a health-check that
the connector module imports cleanly and prints usage instructions.

To search for a specific company, use the Python API directly:

    from porter_verify.connectors.az_ucc import search_az_ucc, to_public_search_results
    results = search_az_ucc("ACME LLC")
    public = to_public_search_results("ACME LLC", results)

Or use the Porter Verify API endpoint:

    GET /ucc/search?state=AZ&company_name=ACME+LLC
"""

import sys

sys.path.insert(0, "src")

from porter_verify.connectors.az_ucc import (  # noqa: E402  (path insert above)
    AZ_UCC_SEARCH_URL,
    search_az_ucc,
    to_public_search_results,
)

if __name__ == "__main__":
    company = sys.argv[1] if len(sys.argv) > 1 else None
    if not company:
        print(
            "Usage: python scripts/refresh_az_ucc.py <company_name>\n"
            "\n"
            "AZ UCC bulk data requires a paid subscription ($1,800/year or $2,000\n"
            "one-time thumb drive from the AZ Secretary of State).\n"
            "\n"
            "This script performs a targeted search for a single company name.\n"
            f"Portal: {AZ_UCC_SEARCH_URL}\n"
            "Contact: 602-542-6187 for UCC public info questions."
        )
        sys.exit(0)

    print(f"Searching AZ UCC for: {company!r} ...")
    try:
        rows = search_az_ucc(company)
    except Exception as exc:
        print(f"ERROR: {exc}")
        print(
            "\nNote: The azsos.gov portal may block automated requests (HTTP 403).\n"
            "If this persists, use a browser-automation approach (Playwright/Selenium)\n"
            "or query the portal manually."
        )
        sys.exit(1)

    results = to_public_search_results(company, rows)
    if not results:
        print("No results found.")
        sys.exit(0)

    print(f"Found {len(results)} filing(s):")
    for r in results:
        print(
            f"  [{r.filing_id}] {r.debtor_name} | {r.secured_party_name or 'N/A'} "
            f"| {r.filing_type} | {r.status} | filed {r.filing_date} "
            f"| confidence {r.match_confidence}%"
        )
