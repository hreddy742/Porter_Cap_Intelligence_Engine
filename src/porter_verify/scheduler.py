"""Background maintenance scheduler."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import sessionmaker

from porter_verify.config import get_settings
from porter_verify.connectors.colorado_ucc import fetch_co_ucc_rows, ingest_co_ucc_rows
from porter_verify.connectors.connecticut_ucc import fetch_ct_ucc_rows, ingest_ct_ucc_rows
from porter_verify.connectors.florida_ucc import ingest_fl_ucc_zip_dir
from porter_verify.connectors.oregon_ucc import fetch_or_ucc_rows, ingest_or_ucc_rows
from porter_verify.db.base import utcnow
from porter_verify.db.session import create_db_engine
from porter_verify.logging_config import get_logger
from porter_verify.services.ofac_refresh import refresh_ofac_files
from porter_verify.services.source_quality import (
    compute_daily_source_quality,
    evaluate_source_health,
)
from porter_verify.services.ucc_intelligence import detect_exit_signals, record_refresh_log

log = get_logger(__name__)

SOURCE_QUALITY_JOB_ID = "source_quality_daily"
OFAC_REFRESH_JOB_ID = "ofac_weekly_refresh"
UCC_WEEKLY_REFRESH_JOB_ID = "ucc_weekly_refresh"
UCC_DAILY_INCREMENTAL_JOB_ID = "ucc_daily_incremental_refresh"
CT_UCC_REFRESH_JOB_ID = "ct_ucc_weekly_refresh"
CO_UCC_REFRESH_JOB_ID = "co_ucc_weekly_refresh"
OR_UCC_REFRESH_JOB_ID = "or_ucc_weekly_refresh"
FL_UCC_REFRESH_JOB_ID = "fl_ucc_weekly_refresh"


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _refresh_ofac_job,
        "cron",
        day_of_week="sun",
        hour=2,
        minute=0,
        id=OFAC_REFRESH_JOB_ID,
        replace_existing=True,
    )
    scheduler.add_job(
        _refresh_ucc_job,
        "cron",
        day_of_week="sun",
        hour=3,
        minute=0,
        id=UCC_WEEKLY_REFRESH_JOB_ID,
        replace_existing=True,
    )
    scheduler.add_job(
        _refresh_ct_ucc_job,
        "cron",
        day_of_week="sun",
        hour=3,
        minute=15,
        id=CT_UCC_REFRESH_JOB_ID,
        replace_existing=True,
    )
    scheduler.add_job(
        _refresh_co_ucc_job,
        "cron",
        day_of_week="sun",
        hour=3,
        minute=30,
        id=CO_UCC_REFRESH_JOB_ID,
        replace_existing=True,
    )
    scheduler.add_job(
        _refresh_or_ucc_job,
        "cron",
        day_of_week="sun",
        hour=3,
        minute=45,
        id=OR_UCC_REFRESH_JOB_ID,
        replace_existing=True,
    )
    scheduler.add_job(
        _refresh_fl_ucc_job,
        "cron",
        day_of_week="sun",
        hour=4,
        minute=0,
        id=FL_UCC_REFRESH_JOB_ID,
        replace_existing=True,
    )
    scheduler.add_job(
        _refresh_ucc_job,
        "cron",
        hour=6,
        minute=0,
        id=UCC_DAILY_INCREMENTAL_JOB_ID,
        replace_existing=True,
    )
    scheduler.add_job(
        _compute_source_quality_job,
        "cron",
        hour=1,
        minute=0,
        id=SOURCE_QUALITY_JOB_ID,
        replace_existing=True,
    )
    return scheduler


def _compute_source_quality_job() -> None:
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        # Compute yesterday's metrics: the day just finished has a complete
        # set of events, whereas "today" is still accumulating them.
        target_date = (utcnow() - timedelta(days=1)).date()
        updated = compute_daily_source_quality(session, metric_date=target_date)
        changed = evaluate_source_health(session)
        log.info(
            "source_quality_job_complete",
            metric_date=str(target_date),
            sources_updated=updated,
            health_changed=changed,
        )


def _refresh_ofac_job() -> None:
    names, aliases = refresh_ofac_files()
    log.info("ofac_refresh_complete", names=names, aliases=aliases)


def _refresh_ucc_job() -> None:
    started_at = utcnow()
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        try:
            signals = detect_exit_signals(session)
            record_refresh_log(
                session,
                state="US",
                refresh_type="INCREMENTAL",
                records_added=signals,
                records_updated=0,
                started_at=started_at,
                status="SUCCESS",
            )
            log.info("ucc_refresh_complete", exit_signals=signals)
        except Exception as exc:
            record_refresh_log(
                session,
                state="US",
                refresh_type="INCREMENTAL",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise


def _refresh_ct_ucc_job() -> None:
    started_at = utcnow()
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        try:
            records = ingest_ct_ucc_rows(session, fetch_ct_ucc_rows())
            exits = detect_exit_signals(session)
            record_refresh_log(
                session,
                state="CT",
                refresh_type="FULL",
                records_added=records,
                records_updated=0,
                started_at=started_at,
                status="SUCCESS",
            )
            log.info("ct_ucc_refresh_complete", records=records, exit_signals=exits)
        except Exception as exc:
            record_refresh_log(
                session,
                state="CT",
                refresh_type="FULL",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise


def _refresh_co_ucc_job() -> None:
    started_at = utcnow()
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        try:
            records = ingest_co_ucc_rows(session, fetch_co_ucc_rows())
            exits = detect_exit_signals(session)
            record_refresh_log(
                session,
                state="CO",
                refresh_type="FULL",
                records_added=records,
                records_updated=0,
                started_at=started_at,
                status="SUCCESS",
            )
            log.info("co_ucc_refresh_complete", records=records, exit_signals=exits)
        except Exception as exc:
            record_refresh_log(
                session,
                state="CO",
                refresh_type="FULL",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise


def _refresh_or_ucc_job() -> None:
    started_at = utcnow()
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        try:
            records = ingest_or_ucc_rows(session, fetch_or_ucc_rows())
            exits = detect_exit_signals(session)
            record_refresh_log(
                session,
                state="OR",
                refresh_type="FULL",
                records_added=records,
                records_updated=0,
                started_at=started_at,
                status="SUCCESS",
            )
            log.info("or_ucc_refresh_complete", records=records, exit_signals=exits)
        except Exception as exc:
            record_refresh_log(
                session,
                state="OR",
                refresh_type="FULL",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise


def _refresh_fl_ucc_job() -> None:
    started_at = utcnow()
    factory = sessionmaker(bind=create_db_engine(get_settings()), expire_on_commit=False)
    with factory() as session:
        try:
            records = ingest_fl_ucc_zip_dir(session, Path(get_settings().fl_ucc_zip_dir))
            exits = detect_exit_signals(session)
            record_refresh_log(
                session,
                state="FL",
                refresh_type="FULL",
                records_added=records,
                records_updated=0,
                started_at=started_at,
                status="SUCCESS",
            )
            log.info("fl_ucc_refresh_complete", records=records, exit_signals=exits)
        except Exception as exc:
            record_refresh_log(
                session,
                state="FL",
                refresh_type="FULL",
                records_added=0,
                records_updated=0,
                started_at=started_at,
                status="FAILED",
                error_text=str(exc),
            )
            raise
