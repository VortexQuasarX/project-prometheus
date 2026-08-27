"""Observation memory for agent runs.

The durable store is the JSON ``observations`` column on ``AgentRun``.
This module is the in-memory accessor (per-run dict keyed by run_id) plus a
helper that mirrors appended observations into the DB row.
"""

from __future__ import annotations

import threading
from typing import Any

_OBSERVATIONS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


class ObservationStore:
    """In-memory per-run observation accessor."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def get(self, run_id: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        if default is None:
            default = {}
        return self._store.get(run_id, default)

    def set(self, run_id: str, observations: dict[str, Any]) -> None:
        self._store[run_id] = observations

    def append(self, run_id: str, key: str, value: Any) -> None:
        self._store.setdefault(run_id, {})[key] = value

    def snapshot(self, run_id: str) -> dict[str, Any]:
        return dict(self._store.get(run_id, {}))


def get_store() -> ObservationStore:
    """Return the process-wide observation store singleton."""
    return ObservationStore()


def append_observation(run_id: str, db: Any, key: str, value: Any) -> None:
    """Append ``key -> value`` to the run's observations (memory + DB JSON)."""
    with _LOCK:
        _OBSERVATIONS.setdefault(run_id, {})[key] = value

    try:
        from app.db import models  # lazy: cross-slice dependency
    except Exception:
        return  # DB slice not present; in-memory only

    try:
        run = db.query(models.AgentRun).filter(models.AgentRun.run_id == run_id).first()
    except Exception:
        return
    if run is None or not hasattr(run, "observations"):
        return
    try:
        current = dict(run.observations or {})
    except Exception:
        current = {}
    current[key] = value
    try:
        run.observations = current
        db.commit()
    except Exception:
        db.rollback()


def observations_for(run_id: str, db: Any) -> dict[str, Any]:
    """Return merged observations: DB JSON (durable) overlaid on memory."""
    merged: dict[str, Any] = {}
    try:
        from app.db import models
    except Exception:
        return dict(_OBSERVATIONS.get(run_id, {}))

    try:
        run = db.query(models.AgentRun).filter(models.AgentRun.run_id == run_id).first()
        if run is not None and hasattr(run, "observations") and run.observations:
            merged.update(dict(run.observations))
    except Exception:
        pass
    merged.update(_OBSERVATIONS.get(run_id, {}))
    return merged


__all__ = ["ObservationStore", "append_observation", "observations_for", "get_store"]
