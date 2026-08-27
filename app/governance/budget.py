"""Budget service (governance/budget.py).

States per DECISIONS B7: normal (<70%) / warning (70-90%) / critical
(90-100%) / exceeded (>=100%) of the daily budget.

``after_spend_recorded`` writes ``BudgetAlert`` rows + SSE ``budget_warning``
on warning/critical/exceeded and auto-sets the kill switch to ``cheap_only``
on exceeded (unless already stricter).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.governance.kill_switch import get_mode, set_mode
from app.governance.policy_engine import get_policy

# Threshold ratios (B7; env-configurable at runtime via module constants).
WARNING_RATIO = 0.7
CRITICAL_RATIO = 0.9
EXCEEDED_RATIO = 1.0

STATUS_ORDER = {"normal": 0, "warning": 1, "critical": 2, "exceeded": 3}
_STRICTER_MODES = {"cache_only": 2, "block_all": 3}  # stricter than cheap_only(1)


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


def _spend_usd() -> tuple[float, float]:
    """Return ``(daily_spend, monthly_spend)`` from usage_records (UTC)."""
    try:
        from app.db import models
    except Exception:
        return 0.0, 0.0

    db = _new_session()
    try:
        rows = db.query(models.UsageRecord).all()
        daily = 0.0
        monthly = 0.0
        now = datetime.now(UTC)
        today = now.date()
        month_start = (now - timedelta(days=30)).date()
        for r in rows:
            cost = float(getattr(r, "cost_usd", 0.0) or 0.0)
            created = getattr(r, "created_at", None)
            if created is None:
                continue
            try:
                date_value = created.date() if hasattr(created, "date") else None
            except Exception:
                date_value = None
            if date_value is None:
                continue
            if date_value >= month_start:
                monthly += cost
            if date_value == today:
                daily += cost
        return round(daily, 6), round(monthly, 6)
    except Exception:
        db.rollback()
        return 0.0, 0.0
    finally:
        try:
            db.close()
        except Exception:
            pass


def compute_state(daily_spend: float) -> str:
    """Map daily spend to normal/warning/critical/exceeded (B7 ratios)."""
    try:
        policy, _ = get_policy()
        budget = float(policy.get("daily_budget_usd", 2.0))
    except Exception:
        budget = 2.0
    if budget <= 0:
        return "exceeded" if daily_spend > 0 else "normal"
    ratio = daily_spend / budget
    if ratio >= EXCEEDED_RATIO:
        return "exceeded"
    if ratio >= CRITICAL_RATIO:
        return "critical"
    if ratio >= WARNING_RATIO:
        return "warning"
    return "normal"


def get_budget_status() -> dict[str, Any]:
    """Exact spec shape for GET /api/v1/budget."""
    daily, monthly = _spend_usd()
    try:
        policy, _ = get_policy()
        daily_budget = float(policy.get("daily_budget_usd", 2.0))
    except Exception:
        daily_budget = 2.0
    status = compute_state(daily)

    recommendations: list[dict[str, Any]] = []
    try:
        from app.cost.recommendations import generate_recommendations  # lazy: cross-slice

        recommendations = generate_recommendations() or []
    except Exception:
        recommendations = []

    return {
        "daily_spend_usd": daily,
        "monthly_spend_usd": monthly,
        "daily_budget_usd": daily_budget,
        "status": status,
        "kill_switch_mode": get_mode(),
        "recommendations": recommendations,
    }


def _write_alert(alert_type: str, severity: str, message: str, metadata: dict[str, Any] | None = None) -> None:
    try:
        from app.db import models

        db = _new_session()
        try:
            row = models.BudgetAlert(
                alert_type=alert_type,
                severity=severity,
                message=message,
                details=metadata or {},
                acknowledged=False,
                created_at=datetime.now(UTC),
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
        pass


def after_spend_recorded() -> None:
    """Recompute budget state after a spend record; alert + escalate."""
    daily, _ = _spend_usd()
    status = compute_state(daily)

    if status == "exceeded":
        _write_alert("budget_exceeded", "exceeded", f"daily spend ${daily:.4f} >= daily budget; kill switch activated", {"daily_spend_usd": daily})
        _emit_sse("budget_warning", payload={"status": status, "daily_spend_usd": daily})
        mode = get_mode()
        if mode not in _STRICTER_MODES:  # cheap_only or off -> escalate to cheap_only
            try:
                set_mode("cheap_only", actor="system", reason="budget exceeded")
            except Exception:
                pass
    elif status == "critical":
        _write_alert("budget_critical", "critical", f"daily spend ${daily:.4f} is >= 90% of daily budget", {"daily_spend_usd": daily})
        _emit_sse("budget_warning", payload={"status": status, "daily_spend_usd": daily})
    elif status == "warning":
        _write_alert("budget_warning", "warning", f"daily spend ${daily:.4f} is >= 70% of daily budget", {"daily_spend_usd": daily})
        _emit_sse("budget_warning", payload={"status": status, "daily_spend_usd": daily})


def get_alerts(limit: int = 20) -> list[dict[str, Any]]:
    """Recent budget/reliability alerts (newest first)."""
    try:
        from app.db import models

        db = _new_session()
        try:
            rows = (
                db.query(models.BudgetAlert)
                .order_by(getattr(models.BudgetAlert, "created_at", models.BudgetAlert.id).desc())
                .limit(max(1, limit))
                .all()
            )
            alerts = []
            for r in rows:
                created = getattr(r, "created_at", None)
                if isinstance(created, str):
                    created_iso = created
                else:
                    try:
                        created_iso = created.isoformat() if created else ""
                    except Exception:
                        created_iso = ""
                alerts.append(
                    {
                        "id": getattr(r, "id", None),
                        "alert_type": getattr(r, "alert_type", ""),
                        "severity": getattr(r, "severity", ""),
                        "message": getattr(r, "message", ""),
                        "metadata": dict(getattr(r, "details", None) or {}),
                        "acknowledged": bool(getattr(r, "acknowledged", False)),
                        "created_at": created_iso,
                    }
                )
            return alerts
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception:
        return []


__all__ = ["compute_state", "get_budget_status", "after_spend_recorded", "get_alerts", "WARNING_RATIO", "CRITICAL_RATIO", "EXCEEDED_RATIO"]
