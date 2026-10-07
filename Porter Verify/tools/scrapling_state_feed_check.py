"""Read-only feasibility check for official state business-registration feeds.

This is reconnaissance only. It requests at most one sample from each listed
official endpoint and prints compact JSON; it does not write records or touch
production connectors.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from scrapling.fetchers import Fetcher


GET_FEEDS = {
    "CO": "https://data.colorado.gov/resource/4ykn-tg5h.json?%24limit=1",
    "CT": "https://data.ct.gov/resource/n7gp-d28j.json?%24limit=1",
    "NY": "https://data.ny.gov/resource/63wc-4exh.json?%24limit=1",
    "OR": "https://data.oregon.gov/resource/tckn-sxa6.json?%24limit=1",
    "TX": "https://comptroller.texas.gov/data-search/franchise-tax?name=Whataburger",
}


def check_get(state: str, url: str) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    try:
        response = Fetcher.get(url, timeout=45)
        body = response.body.decode("utf-8", errors="replace")
        parsed = json.loads(body)
        if isinstance(parsed, list):
            sample = parsed[0] if parsed else None
            count = len(parsed)
        elif isinstance(parsed, dict):
            rows = parsed.get("rows") or parsed.get("data")
            sample = rows[0] if isinstance(rows, list) and rows else parsed
            count = len(rows) if isinstance(rows, list) else 1
        else:
            sample, count = None, 0
        return {
            "state": state,
            "url": url,
            "checked_at": started,
            "http_status": response.status,
            "structured_data": sample is not None,
            "sample_count": count,
            "sample": sample,
        }
    except Exception as exc:
        return {
            "state": state,
            "url": url,
            "checked_at": started,
            "structured_data": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def check_idaho() -> dict:
    state = "ID"
    url = "https://sosbiz.idaho.gov/api/Records/businesssearch"
    started = datetime.now(timezone.utc).isoformat()
    payload = {
        "SEARCH_VALUE": "Micron Technology",
        "STARTS_WITH_YN": "false",
        "ACTIVE_ONLY_YN": "false",
    }
    try:
        response = Fetcher.post(url, json=payload, timeout=45)
        body = response.body.decode("utf-8", errors="replace")
        parsed = json.loads(body)
        rows = parsed if isinstance(parsed, list) else parsed.get("rows", parsed.get("data", []))
        if isinstance(rows, dict):
            row_values = list(rows.values())
        else:
            row_values = rows
        sample = row_values[0] if isinstance(row_values, list) and row_values else None
        return {
            "state": state,
            "url": url,
            "checked_at": started,
            "http_status": response.status,
            "structured_data": sample is not None,
            "sample_count": len(row_values) if isinstance(row_values, list) else 0,
            "sample": sample,
        }
    except Exception as exc:
        return {
            "state": state,
            "url": url,
            "checked_at": started,
            "structured_data": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> None:
    results = []
    with ThreadPoolExecutor(max_workers=len(GET_FEEDS)) as pool:
        futures = {
            pool.submit(check_get, state, url): state
            for state, url in GET_FEEDS.items()
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.append(check_idaho())
    print(json.dumps(sorted(results, key=lambda item: item["state"]), indent=2))


if __name__ == "__main__":
    main()
