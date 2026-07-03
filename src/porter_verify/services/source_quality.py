"""Daily source quality aggregation and health evaluation.

Reads the append-only ``raw_source_events`` log (written per-call by the
verification flow -- see workers/verify_flow.py) and rolls it up into one
``SourceQualityDaily`` row per source per day. ``evaluate_source_health``
then classifies each source's ``health_status`` from its most recent
quality row so ops can see at a glance which sources are degraded, without
disabling anything automatically -- disabling is a deliberate human action
via the ``enabled`` kill switch (see api/routers/sources.py).

Freshness and schema-drift are intentionally conservative in this first
pass:
  - freshness_pass_rate: fraction of successful calls that completed within
    the source's declared ``freshness_sla_hours`` (as a latency proxy) if a
    policy exists; ``None`` when no SLA is configured, so callers can tell
    "not measured" apart from "0% passing".
  - schema_drift_detected: always False for now. Real drift detection would
    require comparing response shape/keys against a stored baseline, which
    is a larger effort deferred to a follow-up; the column is populated so
    downstream consumers (this table's schema) don't need a migration
    later.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from porter_verify.db.base import utcnow
from porter_verify.db.models import RawSourceEvent, SourceQualityDaily, SourceRegistry
from porter_verify.logging_config import get_logger

log = get_logger(__name__)

# Success is any 2xx HTTP-style response code recorded on the event.
_SUCCESS_CODE_MIN = 200
_SUCCESS_CODE_MAX = 299

# Health thresholds, evaluated against the success rate of the most recent
# quality row. A source with zero requests that day is left "unknown"
# rather than penalized -- silence isn't failure.
_HEALTHY_SUCCESS_RATE = 0.95
_DEGRADED_SUCCESS_RATE = 0.80


def compute_daily_source_quality(
    session: Session, *, metric_date: date | None = None
) -> int:
    """Aggregate raw_source_events into one SourceQualityDaily row per source.

    Idempotent: re-running for the same ``metric_date`` updates the existing
    row (unique on source_id + metric_date) rather than duplicating it.

    Returns the number of sources that had at least one event that day.
    """
    target_date = metric_date or utcnow().date()
    day_start = target_date
    day_end = target_date + timedelta(days=1)

    sources = list(session.scalars(select(SourceRegistry)))
    updated = 0
    for source in sources:
        events = list(
            session.scalars(
                select(RawSourceEvent).where(
                    RawSourceEvent.source_id == source.id,
                    RawSourceEvent.occurred_at >= day_start,
                    RawSourceEvent.occurred_at < day_end,
                )
            )
        )
        if not events:
            continue

        request_count = len(events)
        successes = [
            e for e in events
            if e.response_code is not None
            and _SUCCESS_CODE_MIN <= e.response_code <= _SUCCESS_CODE_MAX
        ]
        success_count = len(successes)
        latencies = [e.latency_ms for e in events if e.latency_ms is not None]
        avg_latency_ms = round(sum(latencies) / len(latencies)) if latencies else None
        estimated_cost = float(sum(e.cost_credits for e in events))

        freshness_pass_rate = _freshness_pass_rate(source, successes)

        existing = session.scalar(
            select(SourceQualityDaily).where(
                SourceQualityDaily.source_id == source.id,
                SourceQualityDaily.metric_date == target_date,
            )
        )
        row = existing or SourceQualityDaily(source_id=source.id, metric_date=target_date)
        row.request_count = request_count
        row.success_count = success_count
        row.record_count = success_count
        row.avg_latency_ms = avg_latency_ms
        row.freshness_pass_rate = freshness_pass_rate
        row.estimated_cost = estimated_cost
        row.schema_drift_detected = False
        if existing is None:
            session.add(row)
        updated += 1

    session.commit()
    log.info("source_quality_computed", metric_date=str(target_date), sources_updated=updated)
    return updated


def _freshness_pass_rate(source: SourceRegistry, successes: list[RawSourceEvent]) -> float | None:
    sla_hours = source.policy.freshness_sla_hours if source.policy else None
    if sla_hours is None or not successes:
        return None
    sla_ms = sla_hours * 60 * 60 * 1000
    within_sla = [e for e in successes if e.latency_ms is not None and e.latency_ms <= sla_ms]
    measurable = [e for e in successes if e.latency_ms is not None]
    if not measurable:
        return None
    return len(within_sla) / len(measurable)


def evaluate_source_health(session: Session) -> int:
    """Set each source's health_status from its most recent quality row.

    Does NOT touch ``enabled`` -- disabling a source is a deliberate human
    action via the kill-switch endpoint, never automatic.

    Returns the number of sources whose health_status changed.
    """
    sources = list(session.scalars(select(SourceRegistry)))
    changed = 0
    for source in sources:
        latest = session.scalar(
            select(SourceQualityDaily)
            .where(SourceQualityDaily.source_id == source.id)
            .order_by(SourceQualityDaily.metric_date.desc())
            .limit(1)
        )
        if latest is None or latest.request_count == 0:
            continue

        success_rate = latest.success_count / latest.request_count
        if success_rate >= _HEALTHY_SUCCESS_RATE:
            new_status = "healthy"
        elif success_rate >= _DEGRADED_SUCCESS_RATE:
            new_status = "degraded"
        else:
            new_status = "unhealthy"

        if source.health_status != new_status:
            source.health_status = new_status
            changed += 1

    session.commit()
    log.info("source_health_evaluated", sources_changed=changed)
    return changed
