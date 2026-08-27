"""Approval workflow (governance/approvals.py).

``create_action`` -> pending AgentAction row.
``decide_action`` approve: applies the policy delta through the policy engine,
marks the action applied, moves the run to ``applied``, emits SSE
``action_approved`` + ``action_applied``, audits.
``decide_action`` reject: marks action rejected, run -> ``rejected``, audits.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from app.governance.policy_engine import get_policy, update_policy

ACTION_STATUSES = ("pending", "approved", "rejected", "applied")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _emit_sse(event_type: str, **payload: Any) -> None:
    try:
        from app.core import events  # type: ignore
    except Exception:
        return
    try:
        request_id = payload.pop("request_id", None)
        run_id = payload.pop("run_id", None)
        action_id = payload.pop("action_id", None)
        inner = payload.pop("payload", None)
        body = inner if isinstance(inner, dict) else dict(payload)
        events.emit_sse_event(
            event_type,
            body,
            request_id=request_id if isinstance(request_id, str) else None,
            run_id=run_id if isinstance(run_id, str) else None,
            action_id=action_id if isinstance(action_id, str) else None,
        )
    except Exception:
        return


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


def _models() -> Any:
    from app.db import models  # lazy: cross-slice

    return models


def create_action(
    run_id: str,
    title: str,
    expected_monthly_saving_usd: float,
    risk_level: str,
    latency_impact: str,
    policy_delta: dict[str, Any],
    approval_required: bool = True,
) -> Any:
    """Create a pending AgentAction row and return the ORM object.

    Action ids are ``action_101``, ``action_102``, ... (spec example).
    """
    from app.db import models

    db = _new_session()
    try:
        count = db.query(models.AgentAction).count()
        action_id = f"action_{101 + count}"
        action = models.AgentAction(
            action_id=action_id,
            run_id=run_id,
            title=title,
            description=title,
            expected_monthly_saving_usd=float(expected_monthly_saving_usd),
            risk_level=risk_level,
            latency_impact=latency_impact,
            policy_delta=policy_delta or {},
            approval_required=bool(approval_required),
            status="pending",
            decided_by=None,
            decided_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(action)
        db.commit()
        db.refresh(action)
        return action
    finally:
        try:
            db.close()
        except Exception:
            pass


def list_pending_actions() -> list[Any]:
    """Return all pending AgentAction rows (newest first)."""
    from app.db import models

    db = _new_session()
    try:
        return (
            db.query(models.AgentAction)
            .filter(models.AgentAction.status == "pending")
            .order_by(getattr(models.AgentAction, "created_at", models.AgentAction.id).desc())
            .all()
        )
    finally:
        try:
            db.close()
        except Exception:
            pass


def _action_to_dict(action: Any) -> dict[str, Any]:
    def _iso(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return value.isoformat()
        except Exception:
            return str(value)

    return {
        "action_id": getattr(action, "action_id", ""),
        "run_id": getattr(action, "run_id", ""),
        "title": getattr(action, "title", ""),
        "description": getattr(action, "description", ""),
        "expected_monthly_saving_usd": getattr(action, "expected_monthly_saving_usd", 0.0),
        "risk_level": getattr(action, "risk_level", "low"),
        "latency_impact": getattr(action, "latency_impact", "minimal"),
        "policy_delta": dict(getattr(action, "policy_delta", None) or {}),
        "approval_required": bool(getattr(action, "approval_required", True)),
        "status": getattr(action, "status", "pending"),
        "decided_by": getattr(action, "decided_by", None),
        "decided_at": _iso(getattr(action, "decided_at", None)),
        "created_at": _iso(getattr(action, "created_at", None)),
        "updated_at": _iso(getattr(action, "updated_at", None)),
    }


def decide_action(
    action_id: str,
    decision: Literal["approve", "reject"],
    actor: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Approve or reject an agent action. Returns the action dict."""
    from app.db import models
    from app.governance.audit import append

    db = _new_session()
    try:
        action = db.query(models.AgentAction).filter(models.AgentAction.action_id == action_id).first()
        if action is None:
            raise KeyError(f"action not found: {action_id}")
        if getattr(action, "status", "pending") != "pending":
            raise ValueError(f"action {action_id} is not pending (status={action.status})")

        run = db.query(models.AgentRun).filter(models.AgentRun.run_id == action.run_id).first()

        if decision == "approve":
            # Apply the policy delta through the policy engine.
            current, _ = get_policy()
            merged = {**current, **dict(action.policy_delta or {})}
            _, new_version = update_policy(merged, actor=actor, reason=action.title or "agent action approved")

            action.status = "applied"
            action.decided_by = actor
            action.decided_at = datetime.now(UTC)
            action.updated_at = datetime.now(UTC)
            if run is not None:
                try:
                    run.status = "applied"
                    run.approval_status = "approved"
                    run.updated_at = datetime.now(UTC)
                except Exception:
                    pass
            db.commit()

            _emit_sse("action_approved", action_id=action_id, payload={"actor": actor, "note": note})
            _emit_sse("action_applied", action_id=action_id, payload={"policy_version": new_version})
            append(
                actor=actor,
                role="admin",
                action="agent.action.approved",
                resource=action_id,
                metadata={"run_id": action.run_id, "note": note, "policy_version": new_version},
            )
        else:  # reject
            action.status = "rejected"
            action.decided_by = actor
            action.decided_at = datetime.now(UTC)
            action.updated_at = datetime.now(UTC)
            if run is not None:
                try:
                    run.status = "rejected"
                    run.approval_status = "rejected"
                    run.updated_at = datetime.now(UTC)
                except Exception:
                    pass
            db.commit()
            append(
                actor=actor,
                role="admin",
                action="agent.action.rejected",
                resource=action_id,
                metadata={"run_id": action.run_id, "note": note},
            )

        result = _action_to_dict(action)
        if decision == "approve":
            result["applied"] = True
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            db.close()
        except Exception:
            pass


__all__ = ["create_action", "list_pending_actions", "decide_action", "ACTION_STATUSES"]
