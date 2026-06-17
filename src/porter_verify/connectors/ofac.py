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
from pathlib import Path

# Official OFAC SDN export (the legacy URL 302-redirects here).
OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"

_PLACEHOLDER = "-0-"


def parse_sdn_csv(text: str) -> list[str]:
    """Extract sanctioned names (field index 1) from OFAC SDN CSV text."""

    names: list[str] = []
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if len(row) < 2:
            continue
        name = row[1].strip()
        if name and name != _PLACEHOLDER:
            names.append(name)
    return names


def load_sdn_names(path: str | Path) -> list[str]:
    """Load sanctioned names from a previously downloaded OFAC SDN CSV file."""

    return parse_sdn_csv(Path(path).read_text(encoding="utf-8", errors="ignore"))
