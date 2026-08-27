"""GET /api/v1/health — public liveness + DB check."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Liveness probe: returns service metadata and a DB round-trip check."""
    db_ok = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - defensive
        db_ok = "error"
    return {
        "status": "ok",
        "version": __version__,
        "timestamp": datetime.now(UTC).isoformat(),
        "db": db_ok,
    }
