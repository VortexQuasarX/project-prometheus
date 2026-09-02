"""Engine/session factory for SQLite (MVP).

WAL + busy_timeout + synchronous=NORMAL are applied on every connection;
``check_same_thread=False`` lets FastAPI threadpool workers share the engine.
Single-process design: tests override ``DATABASE_URL`` via env before the
first import of this module.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_engine_options: dict[str, Any] = {"pool_pre_ping": True}
if settings.is_sqlite():
    _engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **_engine_options)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


if settings.is_sqlite():

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for non-request code paths (scripts, background work)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
