"""Guardrail Agent: regex/heuristic safety checks per subagent_01 Section 7.

Checks: PII (email, phone, credit card + Luhn, Aadhaar-like, secret/token
patterns), unsafe content stems, prompt injection phrases, restricted topics,
budget violation (estimated cost vs request_budget_usd) and policy violation.

Behavior:
- PII found + ``pii_masking_enabled`` -> mask and continue (blocked=False,
  ``pii_found`` populated, ``masked_text`` set).
- PII found + masking disabled -> blocked ("pii_detected").
- Unsafe / injection / restricted -> blocked.
- Budget / policy violation -> blocked.

Pure logic; no DB access.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Regex patterns (subagent_01 Section 7)
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b")
_CC_RE = re.compile(r"\b(?:\d[ -]?){13,16}\b")
_AADHAAR_RE = re.compile(r"\b[2-9]\d{3}[ ]?\d{4}[ ]?\d{4}\b")
_SECRET_RE = re.compile(
    r"\b(?:"
    r"sk-[A-Za-z0-9]{20,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|gh[pousr]_[A-Za-z0-9]{36,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|Bearer\s+[A-Za-z0-9._~+/=-]{20,}"
    r")\b"
)
_PEM_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_BASE64_ENTROPY_RE = re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b")

_INJECTION_PATTERNS = (
    re.compile(r"ignore (all|any|previous|above|prior|earlier) (instructions|rules|prompts?)"),
    re.compile(r"ignore your (system )?prompt"),
    re.compile(r"disregard (all |the )?(above|previous|prior|earlier|instructions|rules)"),
    re.compile(r"\bjailbreak\b"),
    re.compile(r"\bdeveloper mode\b"),
    re.compile(r"reveal (your |the |its )?(system )?(prompt|instructions|system prompt)"),
    re.compile(r"\bsystem prompt\b"),
    re.compile(r"\boverride (your )?(rules|instructions|guardrails?|filters?)"),
    re.compile(r"\bno restrictions\b"),
    re.compile(r"\byou are now\b"),
    re.compile(r"\bpretend (to be|you are)\b"),
    re.compile(r"\bact as\b"),
    re.compile(r"\bbypass (the |your )?(guardrails?|filters?|safety|restrictions)"),
    re.compile(r"\bdan\b"),
)

# Unsafe content stems (violence / self-harm / hate / sexual).
_UNSAFE_STEMS = (
    "kill yourself",
    "self harm",
    "self-harm",
    "suicide",
    "murder",
    "torture",
    "sexual abuse",
    "child porn",
    "shoot up",
    "mass shooting",
    "cut yourself",
    "i hate",
    "exterminate",
)

# Restricted topics (weapons / drugs / malware / doxxing / fraud).
_RESTRICTED_TOPICS = (
    "weapon",
    "explosive",
    "bomb making",
    "gun modification",
    "ammunition",
    "drug synthesis",
    "methamphetamine",
    "fentanyl production",
    "cocaine production",
    "malware",
    "ransomware",
    "exploit code",
    "buffer overflow exploit",
    "zero-day exploit",
    "doxx",
    "doxing",
    "swatting",
    "credit card fraud",
    "identity theft",
    "counterfeit money",
    "phishing kit",
    "stolen data",
)

_MASK_MAP: tuple[tuple[re.Pattern[str], str], ...] = (
    (_EMAIL_RE, "[EMAIL]"),
    (_PHONE_RE, "[PHONE]"),
    (_CC_RE, "[CREDIT_CARD]"),
    (_AADHAAR_RE, "[AADHAAR]"),
    (_SECRET_RE, "[REDACTED]"),
    (_PEM_RE, "[REDACTED]"),
    (_BASE64_ENTROPY_RE, "[REDACTED]"),
)


@dataclass
class GuardrailResult:
    """Result of a guardrail check (fixed interface)."""

    blocked: bool
    reasons: list[str]
    risk_level: str
    pii_found: list[str]
    masked_text: str | None = None
    needs_review: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _luhn_valid(number: str) -> bool:
    """Luhn checksum validation (cuts credit-card false positives)."""
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _scan_pii(text: str) -> list[str]:
    """Return a list of PII kind labels found in ``text``."""
    found: list[str] = []
    if _EMAIL_RE.search(text):
        found.append("email")
    if _PHONE_RE.search(text):
        found.append("phone")
    cc_matches = _CC_RE.findall(text)
    if any(_luhn_valid(m) for m in cc_matches):
        found.append("credit_card")
    if _AADHAAR_RE.search(text):
        found.append("aadhaar")
    if _SECRET_RE.search(text) or _PEM_RE.search(text):
        found.append("secret")
    elif _BASE64_ENTROPY_RE.search(text):
        found.append("secret")
    return found


def _mask_pii(text: str) -> str:
    masked = text
    for pattern, replacement in _MASK_MAP:
        masked = pattern.sub(replacement, masked)
    return masked


def _scan_unsafe(text: str) -> list[str]:
    lower = text.lower()
    return [stem for stem in _UNSAFE_STEMS if stem in lower]


def _scan_injection(text: str) -> list[str]:
    lower = text.lower()
    return [pattern.pattern for pattern in _INJECTION_PATTERNS if pattern.search(lower)]


def _scan_restricted(text: str) -> list[str]:
    lower = text.lower()
    return [topic for topic in _RESTRICTED_TOPICS if topic in lower]


def _scan_policy(text: str, policy: dict[str, Any]) -> list[str]:
    """Lightweight policy-violation heuristics."""
    violations: list[str] = []
    allowed = policy.get("allowed_models") or []
    if not allowed:
        violations.append("no allowed models configured")
    named_models = re.findall(r"\b(mock-small|mock-large|bedrock-cheap|bedrock-strong)\b", text)
    for model in named_models:
        if model not in allowed:
            violations.append(f"model {model} not allowed by policy")
    return violations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check(
    query: str,
    *,
    policy: dict[str, Any],
    estimated_request_cost: float | None = None,
) -> GuardrailResult:
    """Pre-flight guardrail check on a user query."""
    reasons: list[str] = []
    blocked = False
    needs_review = False
    metadata: dict[str, Any] = {}
    masked_text: str | None = None

    pii_found = _scan_pii(query)
    if pii_found:
        metadata["pii_kinds"] = pii_found
        masking_enabled = bool(policy.get("pii_masking_enabled", True))
        if masking_enabled:
            masked_text = _mask_pii(query)
            needs_review = True
            reasons.append("pii_masked")
            metadata["pii_masked"] = True
        else:
            blocked = True
            reasons.append("pii_detected")

    unsafe = _scan_unsafe(query)
    if unsafe:
        blocked = True
        reasons.append("unsafe_content")
        metadata["unsafe_stems"] = unsafe

    injection_enabled = bool(policy.get("prompt_injection_detection_enabled", True))
    injection: list[str] = []
    if injection_enabled:
        injection = _scan_injection(query)
    if injection:
        blocked = True
        reasons.append("prompt_injection")
        metadata["injection_patterns"] = injection

    restricted = _scan_restricted(query)
    if restricted:
        blocked = True
        reasons.append("restricted_topic")
        metadata["restricted_topics"] = restricted

    if estimated_request_cost is not None:
        request_budget = float(policy.get("request_budget_usd", 0.05))
        if estimated_request_cost > request_budget:
            blocked = True
            reasons.append("budget_exceeded")
            metadata["estimated_request_cost"] = estimated_request_cost
            metadata["request_budget_usd"] = request_budget

    policy_violations = _scan_policy(query, policy)
    if policy_violations:
        blocked = True
        reasons.append("policy_violation")
        metadata["policy_violations"] = policy_violations

    if blocked:
        risk_level = "high"
    elif pii_found or unsafe or injection or restricted:
        risk_level = "medium"
    else:
        risk_level = "low"

    return GuardrailResult(
        blocked=blocked,
        reasons=reasons,
        risk_level=risk_level,
        pii_found=pii_found,
        masked_text=masked_text,
        needs_review=needs_review,
        metadata=metadata,
    )


def check_response(text: str, policy: dict[str, Any]) -> GuardrailResult:
    """Output-side guardrail: PII leakage and unsafe content in a model answer."""
    reasons: list[str] = []
    blocked = False
    metadata: dict[str, Any] = {}

    pii_found = _scan_pii(text)
    if pii_found:
        reasons.append("pii_in_response")
        metadata["pii_kinds"] = pii_found
        needs_review = True
    else:
        needs_review = False

    unsafe = _scan_unsafe(text)
    if unsafe:
        blocked = True
        reasons.append("unsafe_content_in_response")
        metadata["unsafe_stems"] = unsafe

    risk_level = "high" if blocked else ("medium" if pii_found else "low")
    return GuardrailResult(
        blocked=blocked,
        reasons=reasons,
        risk_level=risk_level,
        pii_found=pii_found,
        masked_text=None,
        needs_review=needs_review,
        metadata=metadata,
    )


__all__ = ["GuardrailResult", "check", "check_response"]
