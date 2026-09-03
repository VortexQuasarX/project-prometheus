"""Alembic migration round-trip test.

Verifies that ``upgrade head`` + ``downgrade base`` runs cleanly
on a fresh, throwaway SQLite database.

The test overrides DATABASE_URL in the environment BEFORE alembic's env.py
reads ``app.core.config.settings``, so the migration targets the fresh DB.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from alembic.config import Config

from alembic import command


def test_alembic_migrations(monkeypatch):
    # Create a fresh temp DB file
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="alembic_test_")
    os.close(fd)
    # Remove the file so alembic creates it from scratch
    os.unlink(db_path)
    db_url = f"sqlite:///{db_path}"

    # Force alembic's env.py to use this URL by overriding the env var
    # that app.core.config.settings reads.
    monkeypatch.setenv("DATABASE_URL", db_url)

    # We must also reload settings so env.py picks up the new value.
    # But since env.py is loaded in a subprocess-like fashion by alembic,
    # we set the URL directly on the config object too.
    from app.core.config import settings
    monkeypatch.setattr(settings, "database_url", db_url)

    # CWD-independent: resolve alembic.ini from the repo root
    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))
    alembic_dir = Path(__file__).resolve().parents[1] / "alembic"
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    try:
        # Upgrade to head
        command.upgrade(alembic_cfg, "head")

        # Downgrade back to base
        command.downgrade(alembic_cfg, "base")
    finally:
        # Clean up the temp database files
        for suffix in ("", "-shm", "-wal"):
            path = db_path + suffix
            if os.path.exists(path):
                os.unlink(path)
