"""Download the official OFAC SDN sanctions list to the local data directory.

Usage:
    python scripts/refresh_ofac.py

The files are downloaded to ``PORTER_OFAC_SDN_PATH`` and ``PORTER_OFAC_ALT_PATH``.
Screening picks them up automatically on next start (or after cache_clear). Run
this on a schedule in production — OFAC publishes updates frequently.
"""

from __future__ import annotations

from pathlib import Path

from porter_verify.config import get_settings
from porter_verify.connectors.ofac import OFAC_ALT_URL, OFAC_SDN_URL
from porter_verify.services.ofac_refresh import refresh_ofac_files


def main() -> None:
    settings = get_settings()
    print(f"Downloading OFAC SDN list from {OFAC_SDN_URL} ...")
    print(f"Downloading OFAC alternate names from {OFAC_ALT_URL} ...")
    names, aliases = refresh_ofac_files()
    print(f"Saved {names:,} sanctioned names to {Path(settings.ofac_sdn_path)}.")
    print(f"Saved {aliases:,} aliases to {Path(settings.ofac_alt_path)}.")


if __name__ == "__main__":
    main()
