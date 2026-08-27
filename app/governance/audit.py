"""Append-only audit trail (governance/audit.py).

Rows are never updated or deleted. ``append`` returns an ``AuditEvent``;
``query`` returns a list of ``AuditEvent`` filtered by actor/action with
pagination.

DB access is lazy + guarded: if the db slice is unavailable the event is
still returned (in-memory) so callers never crash.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditEvent:
    """Audit event record (fixed interface)."""

    event_id: str
    actor: str
    role: str
    action: str
    resource: str
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "actor": self.actor,
            "role": self.role,
            "action": self.action,
            "resource": self.resource,
            "request_id": self.request_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_session() -> Any:
    from app.db import session as _session_mod  # lazy: cross-slice

    for factory_name in ("SessionLocal", "session_factory", "get_db"):
        factory = getattr(_session_mod, factory_name, None)
        if factory is None:
            continue
        try:
            result = factory()
            if hasattr(result, "__next__"):
                return next(result)
            if hasattr(result, "query") or hasattr(result, "execute"):
                return result
        except Exception:
            continue
    raise RuntimeError("no usable session factory found in app.db.session")


def _row_to_event(row: Any) -> AuditEvent:
    def _iso(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return value.isoformat()
        except Exception:
            return str(value)

    return AuditEvent(
        event_id=str(getattr(row, "event_id", "")),
        actor=str(getattr(row, "actor", "")),
        role=str(getattr(row, "role", "")),
        action=str(getattr(row, "action", "")),
        resource=str(getattr(row, "resource", "")),
        request_id=getattr(row, "request_id", None),
        metadata=dict(getattr(row, "details", None) or {}),
        created_at=_iso(getattr(row, "created_at", None)),
    )


def append(
    actor: str,
    role: str,
    action: str,
    resource: str,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Write an audit event (append-only) and return it."""
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc)
    event = AuditEvent(
        event_id=event_id,
        actor=actor,
        role=role,
        action=action,
        resource=resource,
        request_id=request_id,
        metadata=metadata or {},
        created_at=created_at,
    )

    try:
        from app.db import models

        db = _new_session()
        try:
            row = models.AuditEvent(
                event_id=event_id,
                actor=actor,
                role=role,
                action=action,
                resource=resource,
                request_id=request_id,
                metadata=metadata or {},
                created_at=created_at,
            )
            db.add(row)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception:
        pass  # db slice unavailable: in-memory event still returned

    return event


def query(
    actor: str | None = None,
    action: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditEvent]:
    """Query audit events (newest first), optionally filtered."""
    try:
        from app.db import models

        db = _new_session()
        try:
            q = db.query(models.AuditEvent)
            if actor:
                q = q.filter(models.AuditEvent.actor == actor)
            if action:
                q = q.filter(models.AuditEvent.action == action)
            rows = (
                q.order_by(getattr(models.AuditEvent, "created_at", models.AuditEvent.id).desc())
                .offset(max(0, offset))
                .limit(max(1, limit))
                .all()
            )
            return [_row_to_event(r) for r in rows]
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception:
        return []


__all__ = ["AuditEvent", "append", "query"]
