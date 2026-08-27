"""API-key authentication, hashing, and sensitive-data masking.

Keys are stored as SHA-256 hashes and compared with ``hmac.compare_digest``;
the ``role`` field is ``admin`` | ``viewer``. The guardrail slice keeps its
own detection patterns in ``app/agents/guardrail_agent.py``; the patterns in
``MASK_PATTERNS`` here are for log / payload masking only (no duplication of
guardrail logic).
"""

from __future__ import annotations

import hashlib
import hmac
import re

from fastapi import Depends, Header, Request
from sqlalchemy import select, update

from app.core.errors import PrometheusError
from app.db.models import ApiKey, utcnow
from app.db.session import SessionLocal


def hash_api_key(raw: str) -> str:
    """Return the hex SHA-256 digest of a raw API key."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_api_key(raw: str, key_hash: str) -> bool:
    """Constant-time comparison of a raw key against a stored hash."""
    return hmac.compare_digest(hash_api_key(raw), key_hash)


def get_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> ApiKey:
    """FastAPI dependency: any valid (viewer+) API key.

    Returns the ``ApiKey`` ORM row. 401 envelope on missing/invalid key,
    403 envelope when the key is inactive.
    """
    if not x_api_key:
        raise PrometheusError("Missing API key", code="missing_api_key", status_code=401)
    key_hash = hash_api_key(x_api_key)
    with SessionLocal() as session:
        key = session.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
        if key is None:
            raise PrometheusError("Invalid API key", code="invalid_api_key", status_code=401)
        if not key.is_active:
            raise PrometheusError("API key is inactive", code="inactive_api_key", status_code=403)
        try:  # best-effort last-used stamp; never fail the request over it
            session.execute(update(ApiKey).where(ApiKey.id == key.id).values(last_used_at=utcnow()))
            session.commit()
        except Exception:
            session.rollback()
        return key


#: viewer+ alias — the product's core action (chat) is viewer-scoped per D13.
require_api_key = get_api_key


def require_admin(key: ApiKey = Depends(get_api_key)) -> ApiKey:
    """FastAPI dependency: admin role required (403 envelope otherwise)."""
    if key.role != "admin":
        raise PrometheusError("Admin privileges required", code="forbidden", status_code=403)
    return key


# --- sensitive-data masking (logs / error payloads) ---
# Ordered: specific patterns (Aadhaar, cards) run before the generic phone
# pattern so 12-digit numbers are not partially masked as phone numbers.

MASK_PATTERNS: dict[str, tuple[re.Pattern[str], str]] = {
    "email": (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[EMAIL_REDACTED]",
    ),
    "aadhaar": (
        re.compile(r"\b[2-9]\d{3}[ ]?\d{4}[ ]?\d{4}\b"),
        "[AADHAAR_REDACTED]",
    ),
    "credit_card": (
        re.compile(r"\b(?:\d[ -]?){13,16}\b"),
        "[CARD_REDACTED]",
    ),
    "secret_token": (
        re.compile(
            r"\b(?:sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}"
            r"|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|Bearer\s+[A-Za-z0-9._-]{20,}"
            r"|-----BEGIN [A-Z ]*PRIVATE KEY-----)\b"
        ),
        "[TOKEN_REDACTED]",
    ),
    "phone": (
        re.compile(r"\b(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b"),
        "[PHONE_REDACTED]",
    ),
    "base64_high_entropy": (
        re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
        "[REDACTED]",
    ),
}


def mask_sensitive(text: str) -> str:
    """Mask emails, phones, card numbers, Aadhaar-like IDs and tokens in text."""
    if not text:
        return text
    for _, (pattern, replacement) in MASK_PATTERNS.items():
        text = pattern.sub(replacement, text)
    return text
