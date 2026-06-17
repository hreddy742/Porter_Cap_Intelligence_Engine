"""FastAPI application factory.

``create_app`` wires settings, a database session factory, the connector registry,
and the evidence store onto ``app.state`` so tests can inject isolated versions.
A catch-all exception handler returns safe, non-leaky errors.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker

from porter_verify import __version__
from porter_verify.api.routers import companies, health, review, runs, sources, verify
from porter_verify.config import Environment, Settings, get_settings
from porter_verify.connectors.base import ConnectorRegistry
from porter_verify.connectors.factory import build_default_registry
from porter_verify.db.session import create_db_engine
from porter_verify.logging_config import configure_logging, get_logger
from porter_verify.services.evidence import EvidenceStore

log = get_logger(__name__)


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

    app = FastAPI(title="Porter Verify", version=__version__)
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.registry = registry or build_default_registry(session_factory)
    app.state.evidence_store = evidence_store or EvidenceStore(settings.evidence_dir)

    # CORS: permissive for local dev (React on Vite); locked down elsewhere.
    allow_origins = (
        ["http://localhost:5173", "http://localhost:3000"]
        if settings.env is not Environment.PRODUCTION
        else []
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (health, verify, companies, runs, review, sources):
        app.include_router(module.router)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Log the detail server-side; return a safe, generic message to the client.
        log.error("unhandled_error", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    return app


# Module-level app for `uvicorn porter_verify.api.app:app`.
app = create_app()
