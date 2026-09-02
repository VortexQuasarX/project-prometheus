"""ML dataset builder: distill the deterministic rule-based router into a
labeled dataset for the learned routing model.

Features are computed from raw query text (length, question structure,
keyword hits, n-gram stats). Labels come from the deterministic heuristic
router (weak supervision / distillation) so the learned model can be
benchmarked against the rules it replaces.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from app.agents.router_agent import classify

__all__ = ["build_dataset", "Dataset", "FEATURE_NAMES"]

FEATURE_NAMES = [
    "length",
    "words",
    "question_words",
    "reasoning_verbs",
    "long_words_ratio",
    "has_code_terms",
    "avg_word_len",
    "digits_ratio",
]

_SEED_QUERIES: list[tuple[str, str]] = [
    # (query, expected_complexity_class) — cheap = 0, strong = 1
    ("What is AI cost governance?", "cheap"),
    ("How does semantic caching work?", "cheap"),
    ("What is FinOps?", "cheap"),
    ("Define model routing", "cheap"),
    ("What does a guardrail do?", "cheap"),
    ("Explain token budgets", "cheap"),
    ("What is drift detection?", "cheap"),
    ("Summarize prompt injection", "cheap"),
    ("What is an audit trail?", "cheap"),
    ("Tell me about dead-letter queues", "cheap"),
    ("What is idempotency?", "cheap"),
    ("Explain rate limiting", "cheap"),
    ("What is pgvector?", "cheap"),
    ("Describe semantic cache keys", "cheap"),
    ("What is a kill switch?", "cheap"),
    ("Compare the tradeoffs of semantic caching versus prompt caching across "
     "multi-model gateways, analyzing cost, latency, staleness and why each "
     "matters for FinOps forecasting", "strong"),
    ("Design an evaluation strategy for an agentic RAG system that balances "
     "groundedness, latency and cost, and explain how you would productionize it",
     "strong"),
    ("Analyze why our LLM spend doubled last quarter and propose a governance "
     "framework with routing, caching and human-in-the-loop approvals",
     "strong"),
    ("Write a migration plan from a monolithic AI gateway to microservices, "
     "covering data consistency, observability and rollback safety",
     "strong"),
    ("Estimate the total cost of ownership for serving 10M monthly requests "
     "across Bedrock and self-hosted models, including failure modes",
     "strong"),
    ("Explain the mathematical foundations of drift detection using population "
     "stability index and hypothesis testing, with production caveats",
     "strong"),
    ("Architect a multi-tenant policy engine with tenant isolation, versioned "
     "policies and audit-grade change control", "strong"),
    ("How would you debug a p99 latency regression across five microservices "
     "with distributed tracing and cardinality-aware metrics?", "strong"),
    ("Compare dense, sparse and hybrid retrieval for enterprise RAG and justify "
     "when each wins on recall, precision and cost", "strong"),
]


@dataclass
class Dataset:
    """A small tabular dataset: list of feature dicts + labels + raw texts."""

    features: list[dict[str, float]]
    labels: list[int]
    texts: list[str]

    def __len__(self) -> int:
        return len(self.texts)


def extract_features(text: str) -> dict[str, float]:
    """Deterministic hand-crafted features from raw query text."""
    words = text.split()
    lower = text.lower()
    question_words = sum(
        w in ("what", "why", "how", "when", "which", "who", "compare", "explain")
        for w in words
    )
    reasoning_verbs = sum(
        w in ("analyze", "design", "compare", "evaluate", "estimate", "architect",
              "debug", "propose", "migrate", "optimize", "justify")
        for w in lower.replace("?", " ").split()
    )
    long_words = sum(1 for w in words if len(w) >= 10)
    code_terms = int(
        any(t in lower for t in ("sql", "python", "api ", "http", "json", "def ", "class "))
    )
    return {
        "length": float(len(text)),
        "words": float(len(words)),
        "question_words": float(question_words),
        "reasoning_verbs": float(reasoning_verbs),
        "long_words_ratio": (long_words / len(words)) if words else 0.0,
        "has_code_terms": float(code_terms),
        "avg_word_len": (sum(len(w) for w in words) / len(words)) if words else 0.0,
        "digits_ratio": (sum(ch.isdigit() for ch in text) / len(text)) if text else 0.0,
    }


def build_dataset(augment: int = 40, seed: int = 42) -> Dataset:
    """Build the distilled dataset: seed queries + light paraphrase augmentation.

    Labels come from the deterministic heuristic classifier (distillation).
    """
    rng = random.Random(seed)
    features: list[dict[str, float]] = []
    labels: list[int] = []
    texts: list[str] = []

    for text, expected in _SEED_QUERIES:
        category, complexity, _risk = classify(text)
        # heuristic label: complex reasoning or long multi-clause => strong
        label = 1 if (complexity == "complex" or len(text) > 160) else 0
        _ = expected, category
        features.append(extract_features(text))
        labels.append(label)
        texts.append(text)

    # augmentation: small character-level perturbations of each seed query
    for text, _expected in _SEED_QUERIES:
        category, complexity, _risk = classify(text)
        label = 1 if (complexity == "complex" or len(text) > 160) else 0
        for _ in range(max(1, augment // len(_SEED_QUERIES))):
            words = text.split()
            if len(words) < 3:
                continue
            i = rng.randrange(len(words))
            variant = " ".join(
                words[:i] + [words[i] + rng.choice(["", " really", " now", " today"])] + words[i + 1:]
            )
            features.append(extract_features(variant))
            labels.append(label)
            texts.append(variant)

    return Dataset(features=features, labels=labels, texts=texts)


def dataset_summary(dataset: Dataset) -> dict[str, Any]:
    return {
        "rows": len(dataset),
        "strong_ratio": sum(dataset.labels) / len(dataset.labels),
        "feature_names": FEATURE_NAMES,
    }
