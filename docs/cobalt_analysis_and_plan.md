# How Cobalt Intelligence Works — Analysis & Build Plan

Goal of this doc: understand, end to end, how Cobalt Intelligence acquires
Secretary-of-State (SOS) data, then lay out a concrete, phased plan for Porter
Verify to build the equivalent **data-acquisition engine** behind the platform we
already own.

> Sourcing note: assembled from Cobalt's public site, blog, and API docs (links at
> the end). Items we couldn't confirm verbatim are marked **(inferred)** — they are
> the standard way this class of system is built, not claims about Cobalt's private
> code.

---

## Part 1 — How Cobalt works, end to end

### 1.1 What Cobalt actually is
A **primary-source, real-time data provider**, not a KYB app. Every API request goes
**directly to the official SOS website** for the requested state, pulls the *current*
record, and returns it normalized. KYB platforms (Middesk, Alloy) sit **on top** of
this layer. Translation: Cobalt is exactly the **data-acquisition layer** Porter is
now choosing to build; the workflow/scoring/evidence platform on top is what we
already have.

### 1.2 The end-to-end flow

```
 Client ──HTTPS (x-api-key)──▶  Cobalt API
                                   │  enqueue job (searchId)
                                   ▼
                          Per-STATE acquisition worker
                                   │   pick CO/TX/FL… adapter
                                   ▼
            Rotating proxies ──▶ Headless browser / HTTP robot
            CAPTCHA solver  ──▶   • open the state SOS site
                                   • fill the search form, submit
                                   • parse results + open the record
                                   • capture a timestamped SCREENSHOT
                                   ▼
                       Normalize raw HTML → ~22 canonical fields
                                   ▼
                       Cache result (TTL) + store evidence
                                   ▼
   Client ◀── response (or retryId to poll / callback URL if > 30s)
```

### 1.3 The mechanics (the parts that matter)

1. **Per-state automation adapters.** One robot per state that *mimics a manual
   lookup at scale* — navigates that state's specific site, fills its form, parses
   its specific result layout. ~50 of these, each different. **This is the moat.**
2. **Anti-bot infrastructure.** Rotating (residential) proxies, **CAPTCHA solving**,
   human-like navigation — because state sites actively block automation.
3. **Asynchronous execution.** Live scraping is slow (typ. seconds; **Oregon up to
   ~5 min**). If a lookup exceeds ~30s the API returns a **`retryId`**; the client
   **polls** with it or registers a **callback URL**. A **`searchId`** tracks the
   request. Sync-looking API, async engine underneath.
4. **Normalization to ~22 fields.** entity name, status, formation date, entity
   type, registered agent, **officers (28 states)**, filing history, IDs — mapped
   from each state's idiosyncratic output to one schema.
5. **Evidence.** A **timestamped screenshot** of the source record is returned as
   proof of verification.
6. **Resilience.** Retry logic + **configurable fallback to cached data** when a
   state site is down, so requests don't hard-fail.
7. **Coverage tiers.** Entity/status: 50 states. Officers: ~28. UCC: ~11 states.

### 1.4 Why it's hard (the real cost)
The engineering isn't one scraper — it's **50 fragile adapters + anti-bot + 24/7
maintenance** as states redesign sites, add CAPTCHAs, and change layouts. Cobalt's
business *is* maintaining this. Any in-house rebuild inherits that perpetual cost.

---

## Part 2 — What Porter Verify already has vs. what's missing

We are unusually well-positioned: **we already own the entire "platform on top"** that
Middesk/Alloy build around Cobalt.

| Capability | Cobalt | Porter Verify today |
|---|---|---|
| Swappable per-source connector contract | internal | ✅ `SourceConnector` + registry |
| Normalization to canonical fields | ✅ | ✅ `normalization` (status; extend fields) |
| Raw response preserved before parsing | ✅ | ✅ `raw_source_events` |
| Evidence (screenshot + hash, timestamped) | ✅ screenshot | ◑ JSON evidence + WORM hash; **screenshot capture missing** |
| Entity resolution / matching | basic | ✅ conservative resolver |
| Confidence scoring | n/a (raw provider) | ✅ explainable scoring |
| Audit trail | n/a | ✅ append-only audit |
| **Per-state acquisition robots** | ✅ ~50 | ❌ **the core gap** |
| **Anti-bot infra (proxies, CAPTCHA)** | ✅ | ❌ |
| **Async job execution + polling/callback** | ✅ | ◑ runs are synchronous; status fields exist |
| **Result caching + TTL/fallback** | ✅ | ❌ (Redis planned) |

**Conclusion:** to "build Cobalt," we don't rebuild the platform — we build the
**acquisition engine** (per-state robots + anti-bot + async + cache + screenshot) and
plug it into the contract that already exists.

---

## Part 3 — The build plan (phased)

Ordered by **value-per-risk**: legal + cheap first, scraping infra later behind legal
sign-off. Each phase plugs into the existing `SourceConnector` contract.

### Phase A — Async execution backbone *(prereq for live acquisition)*
Live lookups are slow, so runs must be async (Cobalt's `retryId` pattern).
- Move `run_verification` behind a job queue (start simple: a background worker /
  Prefect later). `verification_runs.status` already has `pending/running`.
- Add API: `POST /verify` returns `{run_id}` immediately; `GET /runs/{id}` polls;
  optional callback URL. Dashboard polls run status.
- **Effort: M. Risk: low. No legal dependency.**

### Phase B — Acquisition framework (the robot base class)
A `BrowserAcquisitionConnector` built on **Playwright**, implementing the existing
contract, providing the shared machinery every state adapter reuses:
- headless browser session, configurable **proxy**, **CAPTCHA-solver hook**,
  human-like pacing, **screenshot capture** (feeds our evidence store as a real
  `screenshot` artifact — closes that gap), raw-HTML preservation, retry/backoff.
- **Effort: L. Risk: med. Needs legal sign-off before pointing at any gov site.**

### Phase C — First real adapters (prove both paths)
1. **Colorado (open-data, legal, no scraping):** bulk-ingest connector over the free
   `data.colorado.gov` dataset → real nationwide-quality data with zero legal risk.
   **Best first build.**
2. **One scraping pilot state** (with legal sign-off): implement a single state via
   the Phase B framework end-to-end (search → record → screenshot → normalize) to
   prove the robot path and contract tests.
- **Effort: M each. Risk: CO low / pilot med.**

### Phase D — Caching & freshness
- Cache normalized results with a TTL (Redis or a DB table); serve cached + flag
  staleness (feeds the existing `data_freshness` score); **fallback to cache** when
  a source is down (mirrors Cobalt). Cuts load and cost.
- **Effort: M. Risk: low.**

### Phase E — Anti-bot infrastructure *(scraping tier only)*
- Residential **proxy pool**, a **CAPTCHA-solving** service (e.g. 2Captcha/Anti-
  Captcha) wired into the Phase B hook, per-site rate limiting, robots.txt respect.
- **Effort: M. Risk: high — legal + ToS per state; only after sign-off.**

### Phase F — Scale-out & maintenance
- One adapter per remaining state, prioritized by **Porter's actual lead volume per
  state** (not alphabetical). Add officer (28-state) and UCC (11-state) capabilities.
- **Site-change monitoring:** canary runs + contract tests per adapter so a state
  redesign is caught fast (this is the perpetual cost — budget for it).
- **Effort: XL, ongoing. Risk: med + maintenance.**

### Cross-cutting guardrails (every phase)
- **No scraping without written legal sign-off** (scraping legality varies by state —
  see [`state_source_feasibility.md`](state_source_feasibility.md)).
- Prefer **official APIs / open data / bulk** wherever they exist (cheaper, legal,
  lower-maintenance) before scraping.
- Every connector preserves **raw** + captures **evidence** (already enforced).

---

## Recommended sequence

1. **Phase A** (async backbone) — unblocks everything, no legal dependency.
2. **Phase C.1 — Colorado open-data connector** — first *real* data, zero legal risk.
3. **Phase D** (cache) — cheap reliability + freshness.
4. **Phase B + C.2** — Playwright framework + one scraping pilot state, **once legal
   signs off**.
5. **Phase E/F** — anti-bot infra + per-state scale-out by lead volume.

This delivers real data fast and legally (CO), proves the hard path on one state, and
only then scales the expensive/risky scraping — instead of trying to boil all 50
states at once.

## Sources
- [Cobalt Intelligence — home / how it works](https://cobaltintelligence.com/)
- [Cobalt Intelligence — about (real-time SOS data)](https://cobaltintelligence.com/about)
- [Cobalt API docs (Stoplight)](https://cobaltintelligence.stoplight.io/docs/cobalt-intelligence/0f51bcacc3743-secretary-of-state-api)
- [Cobalt blog — primary-source documents](https://blog.cobaltintelligence.com/post/secretary-of-state-api-instant-access-to-primary-source-documents)
- [Cobalt blog — multi-state coverage & jurisdiction tracking](https://blog.cobaltintelligence.com/post/cobalt-intelligence-secretary-of-state-api-multi-state-coverage-jurisdiction-tracking)
- [Cobalt vs Middesk — data comparison](https://blog.cobaltintelligence.com/post/cobalt-intelligence-vs-middesk-sos-data-comparison-lenders)
- [Cobalt SDK (GitHub)](https://github.com/cobalt-intelligence/cobalt-int-sdk)
