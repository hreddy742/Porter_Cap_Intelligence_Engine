# Source Registry & Connectors

Porter Verify **rents the commodity data layer and owns the platform.** Sources are
swappable behind one contract, selected by capability + state coverage + health.

## The `SourceConnector` contract (Slice 4)

```python
class SourceConnector(Protocol):
    name: str
    capabilities: set[str]   # {"entity","status","officers","ucc","screenshot","ofac"}
    states: set[str]
    def search(self, q: EntityQuery) -> list[RawResult]: ...
    def fetch(self, ref: SourceRef) -> RawRecord: ...
    def capture_evidence(self, ref: SourceRef) -> EvidenceBlob | None: ...
    def health(self) -> SourceHealth: ...
```

Selection is registry-driven: `registry.select(state="TX", capability="status")`.

## MVP sources

| Source | Provides | Access | MVP role |
|--------|----------|--------|----------|
| SOS/KYB vendor (Cobalt/Middesk — chosen in Phase 0) | entity, status, agent, officers | Paid API | Core data layer |
| OFAC / sanctions | SDN + consolidated lists | Free official files | In-flow screening |
| **Mock vendor** (built-in) | deterministic fixtures | local | dev + tests, proves swappability |
| Colorado SOS open data | entity, status, agent | Official bulk CSV | Direct connector for CO |
| Connecticut SOS open data | entity, status | Official SODA API | Direct connector for CT |
| Oregon SOS open data | entity, status, agent, authorized representatives | Official SODA API | Direct active-entity connector for OR |
| Ohio SOS export | entity, status, available agent/address fields | Official CSV/ZIP supplied at refresh | Direct connector for OH |

Salesforce (matching/sync), SAM.gov, and UCC vendors come in later phases.

The direct state connectors are the primary source for their four states. A paid
provider such as Cobalt is not required for these paths, but remains a possible
fallback for fields and states that official datasets do not cover.

## How to add a new connector

1. Implement the `SourceConnector` protocol in `src/porter_verify/connectors/`.
2. Preserve the **raw** response verbatim — do not parse before storing.
3. Add a row to `source_registry` (capabilities, states, cost, health).
4. Add **contract tests** (`tests/`) — the same suite every connector must pass.
5. Never scrape a source where legally/technically risky without explicit approval;
   prefer licensed vendor APIs or approved manual upload.

## Honesty rules

- Never imply "no liens"/"clear" for a state that was **not checked** — record
  `not_checked` explicitly.
- A treated-as-claim EIN is never labeled "IRS-verified."
- Coverage varies by state; "insufficient evidence" is a valid, expected outcome.
