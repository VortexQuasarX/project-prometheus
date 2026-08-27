"""Kill switch (governance/kill_switch.py).

Source of truth is ``policies.body.kill_switch_mode`` (DECISIONS B6/D14).
``set_mode`` writes through the policy engine (bumps policy_version, audit
``kill_switch.set``). ``apply_to_decision`` gates router decisions.

Modes: off / cache_only / cheap_only / block_all.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.governance.policy_engine import KILL_SWITCH_MODES, get_policy, update_policy

BLOCKED_REASON_CACHE_ONLY = "kill_switch_cache_only"
BLOCKED_REASON_CHEAP_ONLY = "kill_switch_cheap_only"
BLOCKED_REASON_BLOCK_ALL = "kill_switch_block_all"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def get_mode() -> str:
    """Return the active kill-switch mode from the policy body."""
    try:
        policy, _ = get_policy()
        mode = policy.get("kill_switch_mode", "off")
        return mode if mode in KILL_SWITCH_MODES else "off"
    except Exception:
        return "off"


def set_mode(mode: str, actor: str, reason: str) -> dict[str, Any]:
    """Set the kill-switch mode through the policy engine.

    Returns ``{kill_switch_mode, previous_mode, active_since, reason}``.
    """
    if mode not in KILL_SWITCH_MODES:
        raise ValueError(f"invalid kill_switch_mode: {mode!r}; expected one of {KILL_SWITCH_MODES}")

    previous_mode = get_mode()
    if previous_mode == mode:
        return {
            "kill_switch_mode": mode,
            "previous_mode": previous_mode,
            "active_since": _now_iso(),
            "reason": reason,
        }

    policy, _ = get_policy()
    new_body = dict(policy)
    new_body["kill_switch_mode"] = mode
    _, new_version = update_policy(new_body, actor=actor, reason=reason)

    try:
        from app.governance.audit import append

        append(
            actor=actor,
            role="system" if actor == "system" else "admin",
            action="kill_switch.set",
            resource="kill_switch",
            metadata={
                "previous_mode": previous_mode,
                "kill_switch_mode": mode,
                "reason": reason,
                "policy_version": new_version,
            },
        )
    except Exception:
        pass

    return {
        "kill_switch_mode": mode,
        "previous_mode": previous_mode,
        "active_since": _now_iso(),
        "reason": reason,
    }


def apply_to_decision(router_decision: str, model: str) -> tuple[str, str | None]:
    """Apply the kill switch to a router decision.

    Returns ``(final_decision, blocked_reason | None)``.
    """
    mode = get_mode()

    if mode == "off":
        return router_decision, None

    if mode == "block_all":
        return router_decision, BLOCKED_REASON_BLOCK_ALL

    if mode == "cache_only":
        if router_decision == "CACHE_ONLY":
            return router_decision, None
        return "CACHE_ONLY", BLOCKED_REASON_CACHE_ONLY

    if mode == "cheap_only":
        try:
            policy, _ = get_policy()
            expensive = set(policy.get("expensive_models", []))
        except Exception:
            expensive = {"mock-large", "bedrock-strong"}
        if router_decision == "STRONG_MODEL" or model in expensive:
            return "CHEAP_MODEL", BLOCKED_REASON_CHEAP_ONLY
        return router_decision, None

    return router_decision, None


__all__ = [
    "get_mode",
    "set_mode",
    "apply_to_decision",
    "KILL_SWITCH_MODES",
    "BLOCKED_REASON_CACHE_ONLY",
    "BLOCKED_REASON_CHEAP_ONLY",
    "BLOCKED_REASON_BLOCK_ALL",
]
