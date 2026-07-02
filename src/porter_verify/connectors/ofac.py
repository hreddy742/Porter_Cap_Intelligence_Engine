"""Real OFAC sanctions list ingestion.

OFAC publishes the SDN list as a free, official CSV (no header): field 0 is the
record number, **field 1 is the name**, field 2 is the type, field 3 the program.
Placeholder cells are the literal ``-0-``. We parse names from that file and feed
them to the screening service.

Refresh the local copy with ``python scripts/refresh_ofac.py`` (downloads the
official file). Screening falls back to a small bundled fixture when no file is
present, so the system runs offline and in tests.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

# Official OFAC SDN export (the legacy URL 302-redirects here).
OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
OFAC_ALT_URL = "https://www.treasury.gov/ofac/downloads/alt.csv"

_PLACEHOLDER = "-0-"


@dataclass(frozen=True)
class SdnEntry:
    record_number: str
    name: str
    program: str | None


@dataclass(frozen=True)
class AltEntry:
    record_number: str
    name: str


def parse_sdn_csv(text: str) -> list[str]:
    """Extract sanctioned names (field index 1) from OFAC SDN CSV text."""

    return [entry.name for entry in parse_sdn_entries(text)]


def parse_sdn_entries(text: str) -> list[SdnEntry]:
    """Extract sanctioned names and programs from OFAC SDN CSV text."""

    entries: list[SdnEntry] = []
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if len(row) < 2:
            continue
        name = row[1].strip()
        if not name or name == _PLACEHOLDER:
            continue
        program = row[3].strip() if len(row) > 3 else ""
        record_number = row[0].strip()
        entries.append(
            SdnEntry(
                record_number=record_number,
                name=name,
                program=program if program != _PLACEHOLDER else None,
            )
        )
    return entries


def parse_alt_entries(text: str) -> list[AltEntry]:
    """Extract alternate names from OFAC ALT CSV text."""

    entries: list[AltEntry] = []
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if len(row) < 4:
            continue
        name = row[3].strip()
        if not name or name == _PLACEHOLDER:
            continue
        entries.append(AltEntry(record_number=row[0].strip(), name=name))
    return entries


def load_sdn_entries(path: str | Path) -> list[SdnEntry]:
    """Load sanctioned names and programs from a previously downloaded SDN CSV file."""

    return parse_sdn_entries(Path(path).read_text(encoding="utf-8", errors="ignore"))


def load_sdn_names(path: str | Path) -> list[str]:
    """Load sanctioned names from a previously downloaded OFAC SDN CSV file."""

    return [entry.name for entry in load_sdn_entries(path)]


def load_alt_entries(path: str | Path) -> list[AltEntry]:
    """Load sanctioned aliases from a previously downloaded OFAC ALT CSV file."""

    return parse_alt_entries(Path(path).read_text(encoding="utf-8", errors="ignore"))
