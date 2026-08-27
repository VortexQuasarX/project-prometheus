"""Project Prometheus — FastAPI application factory.

Local mock mode works with zero AWS credentials (LLM_PROVIDER=mock etc.).
Startup initializes the SQLite schema and seeds demo data if empty.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.middleware import setup_middleware
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables + seed-if-empty on startup."""
    init_db()
    yield


def _cors_origins() -> list[str]:
    value = getattr(settings, "cors_origins", ["http://localhost:3000"])
    if isinstance(value, str):
        return [o.strip() for o in value.split(",") if o.strip()]
    return list(value or ["http://localhost:3000"])


def create_app() -> FastAPI:
    app = FastAPI(
        title="Project Prometheus",
        description="Agentic AI Governance and FinOps Control Plane",
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=[
            "X-API-Key",
            "X-Request-Id",
            "X-Idempotency-Key",
            "Content-Type",
            "Authorization",
        ],
    )
    setup_middleware(app)
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "service": "Project Prometheus",
            "description": "Agentic AI Governance and FinOps Control Plane",
            "version": __version__,
            "docs": "/docs",
        }

    return app


app = create_app()
