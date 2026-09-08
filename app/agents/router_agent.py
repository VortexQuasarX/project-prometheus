"""Router Agent: deterministic query classification and decision routing.

Pure logic, no I/O. Decisions are exactly one of:
CACHE_ONLY, CHEAP_MODEL, STRONG_MODEL, GUARDRAIL_REVIEW, REJECT, CLARIFY.

Mapping (spec examples + subagent_01 Section 3):
- blocked topic            -> REJECT
- suspicious              -> GUARDRAIL_REVIEW
- short FAQ               -> CACHE_ONLY (cache_similarity >= threshold) else CHEAP_MODEL
- long / complex          -> STRONG_MODEL
- ambiguous               -> CLARIFY
- budget critical         -> CHEAP_MODEL
- kill_switch cache_only  -> CACHE_ONLY
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Decision / vocabulary constants
# ---------------------------------------------------------------------------

CACHE_ONLY = "CACHE_ONLY"
CHEAP_MODEL = "CHEAP_MODEL"
STRONG_MODEL = "STRONG_MODEL"
GUARDRAIL_REVIEW = "GUARDRAIL_REVIEW"
REJECT = "REJECT"
CLARIFY = "CLARIFY"

DECISIONS = (CACHE_ONLY, CHEAP_MODEL, STRONG_MODEL, GUARDRAIL_REVIEW, REJECT, CLARIFY)

COMPLEXITY_LEVELS = ("low", "medium", "high")
RISK_LEVELS = ("low", "medium", "high")

DEFAULT_CACHE_SIMILARITY_THRESHOLD = 0.82

# Category keyword sets (checked in priority order).
_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pii": (
        "aadhaar",
        "credit card",
        "card number",
        "ssn",
        "social security",
        "pan number",
        "my email",
        "my phone",
        "my number",
        "password",
        "passcode",
    ),
    "safety": (
        "hack",
        "hacking",
        "weapon",
        "bomb",
        "explosive",
        "malware",
        "ransomware",
        "exploit",
        "doxx",
        "fraud",
        "phishing",
        "drug synthesis",
        "meth",
        "fentanyl",
        "kill someone",
        "self-harm",
        "suicide",
    ),
    "unsupported": (
        "weather",
        "stock price",
        "sports score",
        "news today",
        "who is the president",
        "cricket match",
        "movie times",
        "traffic",
        "currency rate",
        "election results",
    ),
    "cost": (
        "cost",
        "price",
        "pricing",
        "spend",
        "spending",
        "budget",
        "expensive",
        "cheaper",
        "cheap",
        "savings",
        "save money",
        "token cost",
        "finops",
        "bill",
    ),
    "cache": (
        "cache",
        "cached",
        "cache hit",
        "hit rate",
        "ttl",
        "similarity threshold",
        "semantic cache",
        "cache miss",
    ),
    "rag": (
        "rag",
        "document",
        "documents",
        "ingest",
        "retriev",
        "context",
        "knowledge base",
        "chunk",
        "citation",
    ),
    "reasoning": (
        "explain",
        "compare",
        "analyze",
        "analysis",
        "why",
        "how does",
        "difference",
        "between",
        "derive",
        "prove",
        "evaluate tradeoff",
        "what happens if",
        "walk me through",
        "reasoning",
    ),
    "faq": (
        "what is",
        "what's",
        "what are",
        "how to",
        "how do i",
        "define",
        "definition",
        "meaning",
        "when",
        "where",
        "who",
        "which",
        "can you tell me",
        "is it possible",
        "summary",
        "overview",
    ),
}

_QUESTION_WORDS = ("what", "why", "how", "when", "where", "who", "which", "does", "can", "is")
_REASONING_VERBS = (
    "explain",
    "compare",
    "analyze",
    "evaluate",
    "derive",
    "prove",
    "justify",
    "contrast",
    "assess",
    "synthesize",
    "design",
    "optimize",
    "debug",
    "refactor",
)
_CLAUSE_MARKERS = (",", ";", " because ", " but ", " although ", " however ", " whereas ", " and then ")

# Suspicious / risk patterns (keyword heuristics; the guardrail agent owns the
# authoritative regex checks — the router only needs a coarse risk signal).
_RISK_HIGH_TERMS = (
    "ignore previous",
    "ignore all",
    "ignore instructions",
    "jailbreak",
    "dan ",
    "developer mode",
    "reveal system prompt",
    "reveal your prompt",
    "override instructions",
    "no restrictions",
    "pretend",
    "act as",
    "credit card",
    "ssn",
    "aadhaar",
    "hack",
    "exploit",
    "malware",
    "bomb",
    "weapon",
    "doxx",
    "fraud",
    "phishing",
)
_RISK_MEDIUM_TERMS = (
    "password",
    "secret",
    "token",
    "api key",
    "bypass",
    "circumvent",
    "unlock",
    "blocked",
    "block list",
)

_WORD_RE = re.compile(r"[a-z0-9']+")


@dataclass
class RouterDecision:
    """The router's decision object (fixed interface)."""

    decision: str
    model: str
    complexity: str
    category: str
    risk_level: str
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _complexity_score(query: str, tokens: list[str]) -> int:
    score = 0
    n = len(tokens)
    if n >= 40:
        return 6  # hard floor: very long text is always high complexity
    if n <= 7:
        score += 1
    elif n <= 20:
        score += 2
    else:
        score += 3
    lower = query.lower()
    if any(tok in _QUESTION_WORDS for tok in tokens):
        score += 1
    if any(verb in lower for verb in _REASONING_VERBS):
        score += 1
    if any(marker in lower for marker in _CLAUSE_MARKERS):
        score += 1
    return score


def _classify_category(query: str) -> str:
    lower = query.lower()
    for category, keywords in _KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "general"


def classify(query: str) -> tuple[str, str, str]:
    """Return ``(category, complexity, risk)`` for a query (deterministic)."""
    tokens = _tokenize(query)
    category = _classify_category(query)

    score = _complexity_score(query, tokens)
    if score <= 2:
        complexity = "low"
    elif score <= 4:
        complexity = "medium"
    else:
        complexity = "high"

    lower = query.lower()
    risk = "low"
    if any(term in lower for term in _RISK_HIGH_TERMS):
        risk = "high"
    elif any(term in lower for term in _RISK_MEDIUM_TERMS):
        risk = "medium"

    return category, complexity, risk


# ---------------------------------------------------------------------------
# Model pickers
# ---------------------------------------------------------------------------


def _allowed_models(policy: dict[str, Any]) -> list[str]:
    models = policy.get("allowed_models") or []
    return [m for m in models if isinstance(m, str)]


def _pick_cheap_model(policy: dict[str, Any]) -> str:
    from app.providers import get_setting

    allowed = _allowed_models(policy)
    provider = (get_setting("llm_provider", "mock") or "mock").strip().lower()
    if provider == "bedrock":
        order = ("bedrock-cheap", "apac.amazon.nova-micro-v1:0", "mock-small")
    elif provider == "openai":
        order = ("openai-cheap", "gpt-4o-mini", "mock-small")
    else:
        order = ("mock-small", "bedrock-cheap")

    for candidate in order:
        if candidate in allowed:
            return candidate
    return allowed[0] if allowed else "bedrock-cheap"


def _pick_strong_model(policy: dict[str, Any]) -> str:
    from app.providers import get_setting

    allowed = _allowed_models(policy)
    provider = (get_setting("llm_provider", "mock") or "mock").strip().lower()
    if provider == "bedrock":
        order = ("bedrock-strong", "apac.amazon.nova-lite-v1:0", "mock-large")
    elif provider == "openai":
        order = ("openai-strong", "gpt-4o", "mock-large")
    else:
        order = ("mock-large", "bedrock-strong")

    for candidate in order:
        if candidate in allowed:
            return candidate
    return _pick_cheap_model(policy)


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


def decide(
    query: str,
    *,
    budget_status: str,
    policy: dict[str, Any],
    cache_similarity: float | None = None,
    guardrail_risk: str = "low",
    query_category: str | None = None,
) -> RouterDecision:
    """Route a query to one of the six decisions.

    Keyword-only arguments keep the call sites explicit. ``policy`` is the
    active policy body (dict) from ``governance.policy_engine.get_policy``.
    """
    category, complexity, risk = classify(query)
    if query_category:
        category = query_category
    if guardrail_risk in ("high", "blocked"):
        risk = "high"

    threshold = float(
        policy.get("cache_similarity_threshold", DEFAULT_CACHE_SIMILARITY_THRESHOLD)
    )
    kill_switch_mode = policy.get("kill_switch_mode", "off")

    def decision_for(kind: str, model: str, reason: str) -> RouterDecision:
        return RouterDecision(
            decision=kind,
            model=model,
            complexity=complexity,
            category=category,
            risk_level=risk,
            reason=reason,
        )

    # 1. Blocked topics / guardrail hard-block -> REJECT.
    if category in ("safety", "pii") and risk == "high":
        return decision_for(REJECT, "", f"blocked topic: {category}")

    # 2. Kill switch cache_only -> everything becomes CACHE_ONLY.
    if kill_switch_mode == "cache_only":
        return decision_for(CACHE_ONLY, "", "kill switch cache_only")

    # 3. Suspicious but not blocked -> review.
    if risk == "high":
        return decision_for(GUARDRAIL_REVIEW, "", "suspicious query pattern")

    # 4. Budget critical/exceeded -> cheap model.
    if budget_status in ("critical", "exceeded"):
        return decision_for(CHEAP_MODEL, _pick_cheap_model(policy), "budget status " + budget_status)

    # 5. Kill switch cheap_only -> cheap model.
    if kill_switch_mode == "cheap_only":
        return decision_for(CHEAP_MODEL, _pick_cheap_model(policy), "kill switch cheap_only")

    # 6. High similarity -> cache hit path.
    if cache_similarity is not None and cache_similarity >= threshold:
        return decision_for(CACHE_ONLY, "", f"cache similarity {cache_similarity:.3f} >= {threshold}")

    # 7. Unsupported / out of scope -> clarify.
    if category == "unsupported":
        return decision_for(CLARIFY, "", "unsupported query category")

    # 8. Complex / reasoning -> strong model.
    if complexity == "high":
        return decision_for(STRONG_MODEL, _pick_strong_model(policy), "high query complexity")

    # 9. Simple known categories -> cheap model (cache already checked).
    if complexity == "low":
        if category in ("cost", "cache", "rag", "faq", "general"):
            return decision_for(CHEAP_MODEL, _pick_cheap_model(policy), f"simple {category} query")

    # 10. Medium complexity reasoning -> strong; otherwise cheap.
    if complexity == "medium":
        if category == "reasoning":
            return decision_for(STRONG_MODEL, _pick_strong_model(policy), "medium reasoning query")
        if category == "general":
            return decision_for(CLARIFY, "", "ambiguous query")

    # 11. Fallback.
    return decision_for(CHEAP_MODEL, _pick_cheap_model(policy), "default cheap routing")
