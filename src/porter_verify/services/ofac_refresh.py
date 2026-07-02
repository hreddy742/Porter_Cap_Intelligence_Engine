"""Refresh official OFAC source files."""

from __future__ import annotations

from pathlib import Path

import httpx

from porter_verify.config import get_settings
from porter_verify.connectors.ofac import (
    OFAC_ALT_URL,
    OFAC_SDN_URL,
    parse_alt_entries,
    parse_sdn_csv,
)
from porter_verify.services.ofac import clear_ofac_caches


def refresh_ofac_files() -> tuple[int, int]:
    """Download OFAC SDN and alias files; return (name_count, alias_count)."""

    settings = get_settings()
    dest = Path(settings.ofac_sdn_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    alt_dest = Path(settings.ofac_alt_path)
    alt_dest.parent.mkdir(parents=True, exist_ok=True)

    resp = httpx.get(OFAC_SDN_URL, follow_redirects=True, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    names = parse_sdn_csv(resp.text)

    alt_resp = httpx.get(OFAC_ALT_URL, follow_redirects=True, timeout=60)
    alt_resp.raise_for_status()
    alt_dest.write_bytes(alt_resp.content)
    aliases = parse_alt_entries(alt_resp.text)

    clear_ofac_caches()
    return len(names), len(aliases)
