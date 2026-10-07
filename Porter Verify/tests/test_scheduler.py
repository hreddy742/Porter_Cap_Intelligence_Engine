"""Tests for background maintenance scheduling."""

from __future__ import annotations

from fastapi.testclient import TestClient

from porter_verify.api.app import create_app
from porter_verify.config import Settings
from porter_verify.scheduler import (
    CO_UCC_REFRESH_JOB_ID,
    CT_UCC_REFRESH_JOB_ID,
    FL_UCC_REFRESH_JOB_ID,
    OFAC_REFRESH_JOB_ID,
    OR_UCC_REFRESH_JOB_ID,
    UCC_DAILY_INCREMENTAL_JOB_ID,
    UCC_WEEKLY_REFRESH_JOB_ID,
    build_scheduler,
)


def test_scheduler_defines_weekly_ofac_refresh() -> None:
    scheduler = build_scheduler()
    job = scheduler.get_job(OFAC_REFRESH_JOB_ID)

    assert job is not None
    trigger = str(job.trigger)
    assert "day_of_week='sun'" in trigger
    assert "hour='2'" in trigger
    assert "minute='0'" in trigger


def test_scheduler_defines_ucc_refresh_jobs() -> None:
    scheduler = build_scheduler()
    weekly = scheduler.get_job(UCC_WEEKLY_REFRESH_JOB_ID)
    daily = scheduler.get_job(UCC_DAILY_INCREMENTAL_JOB_ID)

    assert weekly is not None
    assert "day_of_week='sun'" in str(weekly.trigger)
    assert "hour='3'" in str(weekly.trigger)
    assert daily is not None
    assert "hour='6'" in str(daily.trigger)

    ct = scheduler.get_job(CT_UCC_REFRESH_JOB_ID)
    assert ct is not None
    assert "day_of_week='sun'" in str(ct.trigger)
    assert "hour='3'" in str(ct.trigger)
    assert "minute='15'" in str(ct.trigger)

    co = scheduler.get_job(CO_UCC_REFRESH_JOB_ID)
    assert co is not None
    assert "day_of_week='sun'" in str(co.trigger)
    assert "hour='3'" in str(co.trigger)
    assert "minute='30'" in str(co.trigger)

    ore = scheduler.get_job(OR_UCC_REFRESH_JOB_ID)
    assert ore is not None
    assert "day_of_week='sun'" in str(ore.trigger)
    assert "hour='3'" in str(ore.trigger)
    assert "minute='45'" in str(ore.trigger)

    fl = scheduler.get_job(FL_UCC_REFRESH_JOB_ID)
    assert fl is not None
    assert "day_of_week='sun'" in str(fl.trigger)
    assert "hour='4'" in str(fl.trigger)
    assert "minute='0'" in str(fl.trigger)


def test_api_starts_scheduler_when_enabled() -> None:
    app = create_app(settings=Settings(scheduler_enabled=True))

    with TestClient(app):
        scheduler = app.state.scheduler
        assert scheduler is not None
        assert scheduler.running is True

    assert scheduler.running is False
