"""Download the official OFAC SDN sanctions list to the local data directory.

Usage:
    python scripts/refresh_ofac.py

The file (~5 MB) is downloaded to ``PORTER_OFAC_SDN_PATH`` (default ./data/ofac_sdn.csv).
Screening picks it up automatically on next start (or after cache_clear). Run this
on a schedule in production — OFAC publishes updates frequently.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from porter_verify.config import get_settings
from porter_verify.connectors.ofac import OFAC_SDN_URL, parse_sdn_csv


def main() -> None:
    settings = get_settings()
    dest = Path(settings.ofac_sdn_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading OFAC SDN list from {OFAC_SDN_URL} ...")
    resp = httpx.get(OFAC_SDN_URL, follow_redirects=True, timeout=60)
    resp.raise_for_status()

    dest.write_bytes(resp.content)
    names = parse_sdn_csv(resp.text)
    print(f"Saved {len(resp.content):,} bytes to {dest} — {len(names):,} sanctioned names.")


if __name__ == "__main__":
    main()
