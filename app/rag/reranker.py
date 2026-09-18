"""Cross-Encoder re-ranker for RAG retrieval context compression.

Scores (query, candidate_chunk) pairs jointly to evaluate semantic coherence,
query coverage, phrase alignment, and context density before prompt injection.
Supports pluggable transformer cross-encoders with a fast zero-dependency fallback.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from app.rag.bm25 import tokenize

logger = logging.getLogger(__name__)

__all__ = ["CrossEncoderReRanker"]


class CrossEncoderReRanker:
    """Joint query-document cross-encoder scoring and re-ranking."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name
        self._model = None
        self._initialized = False

    def _init_transformer_if_available(self) -> bool:
        """Attempt to load sentence-transformers / cross-encoder if installed."""
        if self._initialized:
            return self._model is not None
        self._initialized = True
        if not self.model_name:
            return False
        try:
            from sentence_transformers import CrossEncoder  # type: ignore

            self._model = CrossEncoder(self.model_name)
            logger.info("Loaded transformer CrossEncoder: %s", self.model_name)
            return True
        except Exception as e:
            logger.debug("Transformer CrossEncoder not available (%s), using native cross-attention scoring", e)
            return False

    def score_pair(self, query: str, content: str, title: str = "") -> float:
        """Score a single query-document pair with normalized relevance [0.0, 1.0]."""
        if not query or not content:
            return 0.0

        query_tokens = tokenize(query)
        if not query_tokens:
            return 0.0

        doc_lower = f"{title} {content}".lower()
        content_tokens = tokenize(content)
        content_set = set(content_tokens)

        # 1. Query Term Coverage (how many unique query terms appear in chunk)
        unique_q = set(query_tokens)
        matched_q = sum(1 for q in unique_q if q in content_set)
        coverage_ratio = matched_q / len(unique_q) if unique_q else 0.0

        # 2. Term Density / Frequency
        total_hits = sum(content_tokens.count(q) for q in unique_q)
        density = min(1.0, total_hits / (len(content_tokens) + 10) * 5.0)

        # 3. Exact Phrase & N-gram Matching
        phrase_boost = 0.0
        clean_q = " ".join(query_tokens)
        if clean_q in doc_lower:
            phrase_boost = 0.35
        else:
            # Check 2-grams
            if len(query_tokens) >= 2:
                bigrams = [f"{query_tokens[i]} {query_tokens[i+1]}" for i in range(len(query_tokens) - 1)]
                bigram_hits = sum(1 for b in bigrams if b in doc_lower)
                phrase_boost += min(0.25, (bigram_hits / len(bigrams)) * 0.25)

        # 4. Title Relevance Boost
        title_boost = 0.0
        if title:
            title_tokens = set(tokenize(title))
            if title_tokens:
                title_matches = sum(1 for q in unique_q if q in title_tokens)
                title_boost = min(0.15, (title_matches / len(unique_q)) * 0.15)

        # Joint Cross-Scoring Fusion
        raw_score = (
            coverage_ratio * 0.45 +
            phrase_boost * 0.25 +
            density * 0.15 +
            title_boost * 0.15
        )

        return round(min(1.0, max(0.01, raw_score)), 4)

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Re-rank candidate chunks by joint cross-attention relevance score.
        
        Appends ``rerank_score`` to each chunk dictionary and returns top_k.
        """
        if not candidates:
            return []

        # If transformer cross-encoder is active, use batch model prediction
        if self._init_transformer_if_available() and self._model is not None:
            try:
                pairs = [[query, f"{c.get('title', '')} {c.get('content', '')}"] for c in candidates]
                scores = self._model.predict(pairs)
                for candidate, score in zip(candidates, scores, strict=False):
                    candidate["rerank_score"] = round(float(score), 4)
                candidates.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
                return candidates[:top_k]
            except Exception as e:
                logger.warning("Transformer reranking failed, falling back to native: %s", e)

        # Native Cross-Scoring
        scored = []
        for c in candidates:
            item = dict(c)
            score = self.score_pair(
                query=query,
                content=str(item.get("content") or ""),
                title=str(item.get("title") or item.get("metadata", {}).get("title") or ""),
            )
            item["rerank_score"] = score
            scored.append(item)

        # Sort by rerank_score descending
        scored.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return scored[:top_k]
