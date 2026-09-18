"""Okapi BM25 sparse lexical search implementation for RAG retrieval.

Provides term-frequency inverse-document-frequency (TF-IDF) scoring with document
length normalization. Combined with dense vector search for hybrid retrieval.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

__all__ = ["BM25Index", "tokenize"]

_TOKEN_PATTERN = re.compile(r"\b[a-zA-Z0-9_]+\b")
_STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves",
}


def tokenize(text: str) -> list[str]:
    """Lowercase tokenization with alphanumeric filtering and stop word removal."""
    if not text:
        return []
    words = _TOKEN_PATTERN.findall(text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


class BM25Index:
    """Okapi BM25 index with k1=1.5 and b=0.75."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.corpus_size = 0
        self.avgdl = 0.0
        self.doc_freqs: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.doc_lens: list[int] = []
        self.doc_term_freqs: list[Counter[str]] = []
        self.chunks: list[dict[str, Any]] = []

    def fit(self, chunks: list[dict[str, Any]]) -> None:
        """Build the BM25 index from a list of chunk dictionaries.
        
        Each chunk should have at least ``content`` and a unique identifier.
        """
        self.chunks = list(chunks)
        self.corpus_size = len(chunks)
        self.doc_term_freqs = []
        self.doc_lens = []
        self.doc_freqs = {}

        if self.corpus_size == 0:
            self.avgdl = 0.0
            return

        total_tokens = 0
        for chunk in chunks:
            content = str(chunk.get("content") or "")
            tokens = tokenize(content)
            doc_len = len(tokens)
            self.doc_lens.append(doc_len)
            total_tokens += doc_len

            tf = Counter(tokens)
            self.doc_term_freqs.append(tf)

            for term in tf:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        self.avgdl = total_tokens / self.corpus_size if self.corpus_size > 0 else 0.0

        # Compute Robertson-Spärck Jones IDF
        self.idf = {}
        for term, freq in self.doc_freqs.items():
            self.idf[term] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, top_k: int = 10) -> list[tuple[dict[str, Any], float]]:
        """Search the indexed chunks using BM25 scoring.
        
        Returns a list of ``(chunk, score)`` tuples sorted descending by score.
        """
        if self.corpus_size == 0 or not query:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores: list[float] = [0.0] * self.corpus_size
        for token in query_tokens:
            if token not in self.idf:
                continue
            idf_val = self.idf[token]
            for doc_idx in range(self.corpus_size):
                tf = self.doc_term_freqs[doc_idx].get(token, 0)
                if tf == 0:
                    continue
                doc_len = self.doc_lens[doc_idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self.avgdl or 1.0)))
                scores[doc_idx] += idf_val * (numerator / denominator)

        # Pair scores with original chunks and sort
        scored_chunks = [
            (self.chunks[idx], scores[idx])
            for idx in range(self.corpus_size)
            if scores[idx] > 0.0
        ]
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]
