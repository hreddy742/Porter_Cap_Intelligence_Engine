"""OFAC screening metadata helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from porter_verify.config import get_settings
from porter_verify.connectors.ofac import load_alt_entries, load_sdn_entries
from porter_verify.services.normalization import normalize_name
from porter_verify.services.screening import clear_screening_caches


@lru_cache(maxsize=1)
def get_ofac_metadata_by_name() -> dict[str, tuple[str | None, bool]]:
    settings = get_settings()
    sdn_path = Path(settings.ofac_sdn_path)
    if not sdn_path.exists():
        return {}
    sdn_entries = load_sdn_entries(sdn_path)
    program_by_record = {entry.record_number: entry.program for entry in sdn_entries}
    metadata = {normalize_name(entry.name): (entry.program, False) for entry in sdn_entries}

    alt_path = Path(settings.ofac_alt_path)
    if alt_path.exists():
        for entry in load_alt_entries(alt_path):
            metadata[normalize_name(entry.name)] = (
                program_by_record.get(entry.record_number),
                True,
            )
    return metadata


def clear_ofac_caches() -> None:
    """Clear process-local OFAC caches after refreshing source files."""

    clear_screening_caches()
    get_ofac_metadata_by_name.cache_clear()
