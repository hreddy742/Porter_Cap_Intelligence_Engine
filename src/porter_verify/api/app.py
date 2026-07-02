"""FastAPI application factory.

``create_app`` wires settings, a database session factory, the connector registry,
and the evidence store onto ``app.state`` so tests can inject isolated versions.
A catch-all exception handler returns safe, non-leaky errors.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import update
from sqlalchemy.orm import sessionmaker

from porter_verify import __version__
from porter_verify.api.limiter import limiter
from porter_verify.api.routers import auth, companies, health, ofac, review, runs, sources, ucc, verify
from porter_verify.config import Environment, Settings, get_settings
from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.connectors.factory import build_default_registry
from porter_verify.db.base import utcnow
from porter_verify.db.enums import RunStatus
from porter_verify.db.models.verification import VerificationRun
from porter_verify.db.session import create_db_engine
from porter_verify.logging_config import configure_logging, get_logger
from porter_verify.scheduler import build_scheduler
from porter_verify.services.evidence import EvidenceStore
from porter_verify.services.ucc_intelligence import seed_known_factors

log = get_logger(__name__)

_STUCK_RUN_CUTOFF_MINUTES = 10


def _sweep_stuck_runs(session_factory: sessionmaker) -> None:
    """Mark PENDING runs older than 10 min as FAILED.

    These are runs whose background task was lost when the process restarted.
    Without this, a crashed run blocks the client UI polling forever.
    """
    cutoff = utcnow() - timedelta(minutes=_STUCK_RUN_CUTOFF_MINUTES)
    with session_factory() as session:
        result = session.execute(
            update(VerificationRun)
            .where(
                VerificationRun.status == RunStatus.PENDING,
                VerificationRun.started_at < cutoff,
            )
            .values(status=RunStatus.FAILED, finished_at=utcnow())
        )
        swept = result.rowcount
        session.commit()
    if swept:
        log.warning("stuck_runs_swept", count=swept, cutoff_minutes=_STUCK_RUN_CUTOFF_MINUTES)
    else:
        log.info("stuck_run_sweep_clean")


def create_app(
    *,
    settings: Settings | None = None,
    session_factory: sessionmaker | None = None,
    registry: ConnectorRegistry | None = None,
    evidence_store: EvidenceStore | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    if session_factory is None:
        engine = create_db_engine(settings)
        session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        with session_factory() as session:
            seed_known_factors(session)
        # Sweep any runs left PENDING from a previous process restart.
        _sweep_stuck_runs(session_factory)
        if settings.scheduler_enabled:
            scheduler = build_scheduler()
            scheduler.start()
            app.state.scheduler = scheduler
            log.info("scheduler_started")
        try:
            yield
        finally:
            scheduler = app.state.scheduler
            if scheduler is not None and scheduler.running:
                scheduler.shutdown(wait=False)
                log.info("scheduler_stopped")

    app = FastAPI(title="Porter Verify", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.registry = registry or build_default_registry(session_factory)
    app.state.evidence_store = evidence_store or EvidenceStore(settings.evidence_dir)
    app.state.scheduler = None

    # Rate limiter — slowapi reads app.state.limiter on each decorated request.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS: permissive for local dev; env-var-driven for staging/production.
    if settings.env is not Environment.PRODUCTION:
        allow_origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ]
    elif settings.allowed_origins:
        allow_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    else:
        allow_origins = []

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (auth, health, verify, companies, runs, review, sources, ucc, ofac):
        app.include_router(module.router)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_error", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    return app


# Module-level app for `uvicorn porter_verify.api.app:app`.
app = create_app()
