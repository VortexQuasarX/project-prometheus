"""Deterministic, word-boundary-aware text chunking for RAG.

``chunk_size`` is an approximate character budget per chunk (400 chars ≈ 100
tokens at the project's ``len//4`` token simulation); ``overlap`` is the
number of characters shared between consecutive chunks. Both are aligned to
word boundaries so chunks never split words.
"""
from __future__ import annotations

import re
from typing import Any

__all__ = ["chunk_document", "chunk_text"]

_WS_RE = re.compile(r"\s+")


def chunk_text(content: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """Split ``content`` into overlapping word-aligned chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")

    words = _WS_RE.split((content or "").strip())
    if not words or words == [""]:
        return []

    chunks: list[str] = []
    start = 0
    total = len(words)
    while start < total:
        end = start
        size = 0
        while end < total:
            word_len = len(words[end]) + (1 if end > start else 0)
            if size + word_len > chunk_size and end > start:
                break
            size += word_len
            end += 1
        chunk = " ".join(words[start:end])
        if chunk:
            chunks.append(chunk)
        if end >= total:
            break
        # Rewind `start` by up to `overlap` characters (word-aligned).
        rewound = 0
        cursor = end - 1
        while cursor >= start and rewound < overlap:
            rewound += len(words[cursor]) + (1 if cursor < end - 1 else 0)
            cursor -= 1
        next_start = cursor + 1
        start = next_start if next_start > start else end
    return chunks


def chunk_document(
    document_id: str,
    title: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Chunk a document into chunk dicts.

    Each dict (contract): ``{document_id, title, chunk_id (doc_xx_chunk_NN),
    index, content, token_count, metadata}``. ``metadata`` is merged with
    ``document_id``/``title`` so search results stay self-describing.
    """
    base = dict(metadata or {})
    base.setdefault("document_id", document_id)
    base.setdefault("title", title)

    chunks: list[dict[str, Any]] = []
    for index, text in enumerate(chunk_text(content), start=1):
        chunks.append(
            {
                "document_id": document_id,
                "title": title,
                "chunk_id": f"{document_id}_chunk_{index:02d}",
                "index": index,
                "content": text,
                "token_count": max(1, len(text) // 4),
                "metadata": {**base, "chunk_index": index},
            }
        )
    return chunks
