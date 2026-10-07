"""OFAC sanctions screening.

Screens a name (company or officer) against the OFAC sanctions list. In production
the list is the official, freely-published SDN + consolidated files, refreshed
daily; here we ship a tiny representative fixture so the flow and tests run offline.

Matching is fuzzy (names rarely match exactly) with a conservative threshold; any
hit at or above the threshold is flagged for human review and drives the overall
status to RISK_FLAG. The only real engineering here is the threshold (plan §8.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from porter_verify.config import get_settings
from porter_verify.connectors.ofac import load_alt_entries, load_sdn_names
from porter_verify.logging_config import get_logger
from porter_verify.services.entity_resolution import name_sim
from porter_verify.services.normalization import normalize_name

log = get_logger(__name__)

SCREENING_VERSION = "ofac-v1"

# Default fuzzy threshold. A hit at/above this is flagged.
DEFAULT_THRESHOLD = 0.85

# Offline fallback used when the official OFAC file has not been downloaded.
_FIXTURE_LIST: list[str] = [
    "Specially Designated National Corp",
    "Blocked Persons Holdings LLC",
    "Sanctioned Trading Company",
]


@lru_cache(maxsize=1)
def get_sanctions_list() -> list[str]:
    """Return the screening list: the real OFAC file if present, else the fixture.

    Cached for the process. Call ``get_sanctions_list.cache_clear()`` after
    refreshing the OFAC file to pick up the new list.
    """

    path = Path(get_settings().ofac_sdn_path)
    if path.exists():
        names = load_sdn_names(path)
        alt_path = Path(get_settings().ofac_alt_path)
        if alt_path.exists():
            names.extend(entry.name for entry in load_alt_entries(alt_path))
        if names:
            log.info("ofac_list_loaded", source=str(path), count=len(names))
            return names
    log.info("ofac_list_fixture", count=len(_FIXTURE_LIST))
    return _FIXTURE_LIST


def clear_screening_caches() -> None:
    """Clear process-local OFAC screening caches after refreshing source files."""

    get_sanctions_list.cache_clear()


@dataclass(frozen=True)
class ScreeningMatch:
    sanctioned_name: str
    score: float


@dataclass(frozen=True)
class ScreeningResult:
    hit: bool
    query_name: str
    matches: list[ScreeningMatch] = field(default_factory=list)
    threshold: float = DEFAULT_THRESHOLD
    version: str = SCREENING_VERSION


def screen(
    name: str,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    sanctions_list: list[str] | None = None,
) -> ScreeningResult:
    """Screen ``name`` against the sanctions list; return all matches >= threshold.

    The full OFAC list has ~17k names, so we first block on a shared normalized
    token before the expensive fuzzy compare. A name with zero shared tokens cannot
    reach a 0.85 fuzzy threshold, so this is safe (no false negatives) and fast.
    """

    candidates = sanctions_list if sanctions_list is not None else get_sanctions_list()
    query_tokens = set(normalize_name(name).split())
    matches = [
        ScreeningMatch(sanctioned_name=entry, score=sim)
        for entry in candidates
        if query_tokens & set(normalize_name(entry).split())
        and (sim := name_sim(name, entry)) >= threshold
    ]
    matches.sort(key=lambda m: m.score, reverse=True)
    return ScreeningResult(hit=bool(matches), query_name=name, matches=matches, threshold=threshold)
