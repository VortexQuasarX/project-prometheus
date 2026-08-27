"""Reset the demo database and vector store, then re-seed (scripts/reset_demo.py).

Derives the SQLite path from ``settings.database_url``, disposes the shared
engine, deletes the database file (plus ``-wal`` / ``-shm`` sidecars) and the
local vector-store JSONL under ``settings.data_dir``, then re-runs
:func:`seed_demo.main` so the recruiter demo is back to a pristine,
deterministic state.

Run from the repository root:

    python scripts/reset_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import seed_demo  # noqa: E402  (scripts/seed_demo.py, same directory)
from sqlalchemy.engine import make_url  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.session import engine  # noqa: E402


def _sqlite_path(database_url: str) -> Path | None:
    """Resolve the SQLite file path; None for in-memory databases."""
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite") or not url.database:
        return None
    database = url.database
    if database == ":memory:":
        return None
    path = Path(database)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _delete_file(path: Path) -> bool:
    try:
        if path.exists():
            path.unlink()
            return True
    except OSError:
        pass
    return False


def reset() -> dict[str, Any]:
    """Delete DB + vector store and re-run the demo seed. Returns the seed summary."""
    removed: dict[str, list[str]] = {"database": [], "vector_store": []}

    engine.dispose()

    db_path = _sqlite_path(settings.database_url)
    if db_path is not None:
        for candidate in (db_path, db_path.with_suffix(".db-wal"), db_path.with_suffix(".db-shm")):
            if _delete_file(candidate):
                removed["database"].append(str(candidate))
    else:
        print("In-memory database: nothing to delete on disk.")

    for store_file in (settings.data_path("vector_store.jsonl"), settings.data_path("vector_store.jsonl.tmp")):
        if _delete_file(store_file):
            removed["vector_store"].append(str(store_file))

    print("Removed:", removed)

    summary = seed_demo.main()
    summary["removed"] = removed
    return summary


if __name__ == "__main__":
    reset()
