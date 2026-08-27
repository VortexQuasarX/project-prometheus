"""Citation assembly for RAG responses (spec citation shape)."""
from __future__ import annotations

from typing import Any

__all__ = ["build_citations"]

#: Snippet length cap per the contract ("first ~180 chars").
SNIPPET_CHARS = 180


def _snippet(content: str, limit: int = SNIPPET_CHARS) -> str:
    text = " ".join((content or "").split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut + "…"


def build_citations(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build citation dicts ``{document_id, title, chunk_id, snippet}``.

    ``chunks`` are the dicts returned by ``Retriever.retrieve``
    (``{document_id, chunk_id, content, score, metadata}``).
    """
    citations: list[dict[str, Any]] = []
    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        title = chunk.get("title") or metadata.get("title") or ""
        citations.append(
            {
                "document_id": chunk.get("document_id", ""),
                "title": title,
                "chunk_id": chunk.get("chunk_id", ""),
                "snippet": _snippet(str(chunk.get("content") or "")),
            }
        )
    return citations
