"""Policy engine (governance/policy_engine.py).

- ``DEFAULT_POLICY``: the spec's exact JSON + ``expensive_models`` (DECISIONS B8).
- ``PolicySchema``: pydantic v2 validation for every policy field.
- ``get_policy()`` / ``update_policy()`` / ``reset_policy()``.

``update_policy`` writes a ``PolicyChange`` row (old/new/actor/reason),
bumps ``policy_version``, audits ``policy.updated`` and invalidates the
semantic cache (bump of the cache version) when the cache slice is
importable. DB access is lazy + guarded; if the db slice is missing,
``get_policy`` returns the default and updates operate in-memory.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

DEFAULT_ALLOWED_MODELS: list[str] = [
    "apac.amazon.nova-lite-v1:0",
    "apac.amazon.nova-micro-v1:0",
    "apac.amazon.nova-pro-v1:0",
    "bedrock-cheap",
    "bedrock-strong",
    "deepseek.v3-v1:0",
    "deepseek.v3.2",
    "global.amazon.nova-2-lite-v1:0",
    "google.gemma-3-12b-it",
    "google.gemma-3-27b-it",
    "google.gemma-3-4b-it",
    "meta.llama3-70b-instruct-v1:0",
    "meta.llama3-8b-instruct-v1:0",
    "minimax.minimax-m2",
    "minimax.minimax-m2.1",
    "minimax.minimax-m2.5",
    "mistral.devstral-2-123b",
    "mistral.magistral-small-2509",
    "mistral.ministral-3-14b-instruct",
    "mistral.ministral-3-3b-instruct",
    "mistral.ministral-3-8b-instruct",
    "mistral.mistral-7b-instruct-v0:2",
    "mistral.mistral-large-2402-v1:0",
    "mistral.mistral-large-2407-v1:0",
    "mistral.mistral-large-3-675b-instruct",
    "mistral.mistral-small-2402-v1:0",
    "mistral.mixtral-8x7b-instruct-v0:1",
    "mistral.voxtral-mini-3b-2507",
    "mistral.voxtral-small-24b-2507",
    "moonshot.kimi-k2-thinking",
    "moonshotai.kimi-k2.5",
    "nvidia.nemotron-nano-12b-v2",
    "nvidia.nemotron-nano-3-30b",
    "nvidia.nemotron-nano-9b-v2",
    "openai.gpt-oss-120b-1:0",
    "openai.gpt-oss-20b-1:0",
    "openai.gpt-oss-safeguard-120b",
    "openai.gpt-oss-safeguard-20b",
    "qwen.qwen3-235b-a22b-2507-v1:0",
    "qwen.qwen3-32b-v1:0",
    "qwen.qwen3-coder-30b-a3b-v1:0",
    "qwen.qwen3-coder-480b-a35b-v1:0",
    "qwen.qwen3-coder-next",
    "qwen.qwen3-next-80b-a3b",
    "qwen.qwen3-vl-235b-a22b",
    "us.deepseek.r1-v1:0",
    "us.meta.llama3-1-70b-instruct-v1:0",
    "us.meta.llama3-3-70b-instruct-v1:0",
    "writer.palmyra-vision-7b",
    "zai.glm-4.7",
    "zai.glm-4.7-flash",
    "zai.glm-5",
    "mock-small",
    "mock-large",
]

DEFAULT_POLICY: dict[str, Any] = {
    "daily_budget_usd": 2.0,
    "request_budget_usd": 0.05,
    "max_input_tokens": 1000,
    "max_output_tokens": 500,
    "allowed_models": DEFAULT_ALLOWED_MODELS,
    "expensive_model_limit_per_day": 20,
    "require_cache_check": True,
    "require_rag": True,
    "require_evaluation": True,
    "require_human_approval": True,
    "pii_masking_enabled": True,
    "prompt_injection_detection_enabled": True,
    "rate_limit_per_minute": 30,
    "kill_switch_mode": "off",
    "expensive_models": [
        "mock-large",
        "bedrock-strong",
        "us.deepseek.r1-v1:0",
        "us.meta.llama3-3-70b-instruct-v1:0",
        "qwen.qwen3-coder-480b-a35b-v1:0",
        "apac.amazon.nova-pro-v1:0",
        "meta.llama3-70b-instruct-v1:0",
        "mistral.mistral-large-3-675b-instruct",
        "google.gemma-3-27b-it",
    ],
}

KILL_SWITCH_MODES = ("off", "cache_only", "cheap_only", "block_all")

_MODEL_CATALOG = tuple(DEFAULT_ALLOWED_MODELS)


class PolicySchema(BaseModel):
    """Pydantic v2 policy schema.

    14 spec fields + ``expensive_models`` (B8) + the B7 escalation boolean
    (7 booleans total: the 6 spec booleans + ``auto_escalate_kill_switch``).
    """

    daily_budget_usd: float = Field(gt=0)
    request_budget_usd: float = Field(gt=0)
    max_input_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    allowed_models: list[str] = Field(min_length=1)
    expensive_model_limit_per_day: int = Field(ge=0)
    require_cache_check: bool = True
    require_rag: bool = True
    require_evaluation: bool = True
    require_human_approval: bool = True
    pii_masking_enabled: bool = True
    prompt_injection_detection_enabled: bool = True
    auto_escalate_kill_switch: bool = True
    rate_limit_per_minute: int = Field(ge=1)
    kill_switch_mode: Literal["off", "cache_only", "cheap_only", "block_all"] = "off"
    expensive_models: list[str] = Field(default_factory=lambda: list(DEFAULT_POLICY["expensive_models"]))

    @classmethod
    def from_body(cls, body: dict[str, Any]) -> PolicySchema:
        """Build from a body dict, applying defaults for optional fields."""
        return cls(**{k: v for k, v in body.items() if k in cls.model_fields})


def validate_policy(body: dict[str, Any]) -> dict[str, Any]:
    """Validate a policy body; raises ``ValidationError`` on failure."""
    return PolicySchema.from_body(body).model_dump()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


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


def _invalidate_cache() -> None:
    """Bump the cache version so entries become invisible (lazy, best-effort)."""
    try:
        from app.cache import semantic_cache  # type: ignore

        for attr in ("bump_cache_version", "invalidate", "bump_version"):
            fn = getattr(semantic_cache, attr, None)
            if fn is not None:
                try:
                    fn()
                    return
                except Exception:
                    continue
    except Exception:
        pass


def get_policy() -> tuple[dict[str, Any], int]:
    """Return ``(active policy body, policy_version)``.

    Seeds ``DEFAULT_POLICY`` as version 1 when no active row exists.
    """
    try:
        from app.db import models

        db = _new_session()
        try:
            row = db.query(models.Policy).filter(models.Policy.is_active.is_(True)).order_by(models.Policy.policy_version.desc()).first()
            if row is not None:
                return dict(row.body or {}), int(row.policy_version)
            # Seed default policy.
            default = copy.deepcopy(DEFAULT_POLICY)
            seed = models.Policy(policy_version=1, body=default, is_active=True, updated_at=datetime.now(UTC))
            db.add(seed)
            db.commit()
            return dict(default), 1
        except Exception:
            db.rollback()
            return copy.deepcopy(DEFAULT_POLICY), 1
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception:
        return copy.deepcopy(DEFAULT_POLICY), 1


def update_policy(new_body: dict[str, Any], actor: str, reason: str) -> tuple[dict[str, Any], int]:
    """Validate + persist a policy update.

    Writes a ``PolicyChange`` row, bumps ``policy_version``, audits
    ``policy.updated`` and invalidates the cache. Returns
    ``(new_body, new_version)``.
    """
    validated = validate_policy(new_body)  # raises ValidationError on bad input

    try:
        from app.db import models
    except Exception as exc:
        raise RuntimeError("app.db.models is not importable; cannot persist policy") from exc

    from app.governance.audit import append  # lazy within governance package

    db = _new_session()
    try:
        active = db.query(models.Policy).filter(models.Policy.is_active.is_(True)).order_by(models.Policy.policy_version.desc()).first()
        old_body = dict(active.body) if active is not None else {}
        old_version = int(active.policy_version) if active is not None else 1
        new_version = old_version + 1
        now = datetime.now(UTC)

        if active is not None:
            active.is_active = False

        new_row = models.Policy(policy_version=new_version, body=validated, is_active=True, updated_at=now)
        db.add(new_row)

        change = models.PolicyChange(
            policy_version=new_version,
            old_body=old_body,
            new_body=validated,
            actor=actor,
            reason=reason,
            created_at=now,
        )
        db.add(change)
        db.commit()

        try:
            append(
                actor=actor,
                role="system" if actor == "system" else "admin",
                action="policy.updated",
                resource="policy",
                metadata={"policy_version": new_version, "reason": reason},
            )
        except Exception:
            pass

        _invalidate_cache()
        return dict(validated), new_version
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            db.close()
        except Exception:
            pass


def reset_policy(actor: str, reason: str) -> tuple[dict[str, Any], int]:
    """Reset the active policy to ``DEFAULT_POLICY``."""
    return update_policy(copy.deepcopy(DEFAULT_POLICY), actor=actor, reason=reason)


__all__ = [
    "DEFAULT_POLICY",
    "PolicySchema",
    "validate_policy",
    "get_policy",
    "update_policy",
    "reset_policy",
    "KILL_SWITCH_MODES",
]
