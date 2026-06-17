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

from porter_verify.services.entity_resolution import name_sim

SCREENING_VERSION = "ofac-v1"

# Default fuzzy threshold. A hit at/above this is flagged.
DEFAULT_THRESHOLD = 0.85

# Representative sample of sanctioned names. Real deployment loads the official
# OFAC files into this structure.
_SANCTIONS_LIST: list[str] = [
    "Specially Designated National Corp",
    "Blocked Persons Holdings LLC",
    "Sanctioned Trading Company",
]


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
    """Screen ``name`` against the sanctions list; return all matches >= threshold."""

    candidates = sanctions_list if sanctions_list is not None else _SANCTIONS_LIST
    matches = [
        ScreeningMatch(sanctioned_name=entry, score=sim)
        for entry in candidates
        if (sim := name_sim(name, entry)) >= threshold
    ]
    matches.sort(key=lambda m: m.score, reverse=True)
    return ScreeningResult(hit=bool(matches), query_name=name, matches=matches, threshold=threshold)
