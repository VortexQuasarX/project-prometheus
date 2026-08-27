"""In-memory vector store with JSONL persistence.

Works with NO database (spec: "LocalVectorStore must work without
database"). State lives in memory and is persisted to
``<settings.data_dir>/vector_store.jsonl`` on every mutation; loading on
init makes RAG/cache state survive restarts. Embeddings are L2-normalized,
so cosine similarity equals the dot product and ``score`` is in [0, 1] for
valid vectors.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from app.providers import get_setting
from app.providers.embeddings.mock_embeddings import cosine_similarity
from app.vector.base import VectorStore

logger = logging.getLogger(__name__)


class LocalVectorStore(VectorStore):
    """No-database vector store: in-memory list + JSONL persistence."""

    provider_name = "local"

    def __init__(self, data_dir: str | Path | None = None) -> None:
        resolved = Path(data_dir or get_setting("data_dir", "data") or "data")
        self._path = resolved / "vector_store.jsonl"
        self._lock = threading.RLock()
        self._entries: list[dict[str, Any]] = []
        self._load()

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if isinstance(entry, dict) and "chunk_id" in entry:
                        self._entries.append(entry)
        except (OSError, json.JSONDecodeError):
            logger.warning("Could not read %s; starting with an empty store", self._path)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".jsonl.tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            for entry in self._entries:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        os.replace(tmp_path, self._path)

    # ------------------------------------------------------------------
    # VectorStore
    # ------------------------------------------------------------------
    def upsert(
        self,
        document_id: str,
        chunk_id: str,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "document_id": document_id,
            "chunk_id": chunk_id,
            "content": content,
            "embedding": [float(value) for value in embedding],
            "metadata": dict(metadata or {}),
        }
        with self._lock:
            for index, existing in enumerate(self._entries):
                if (
                    existing.get("document_id") == document_id
                    and existing.get("chunk_id") == chunk_id
                ):
                    self._entries[index] = entry
                    break
            else:
                self._entries.append(entry)
            self._save()

    def search(self, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        with self._lock:
            scored = [
                (cosine_similarity(embedding, entry.get("embedding") or []), entry)
                for entry in self._entries
            ]
            scored.sort(key=lambda pair: pair[0], reverse=True)
            limit = max(0, int(top_k))
            return [
                {
                    "document_id": entry["document_id"],
                    "chunk_id": entry["chunk_id"],
                    "content": entry["content"],
                    "score": score,
                    "metadata": dict(entry.get("metadata") or {}),
                }
                for score, entry in scored[:limit]
            ]

    def delete_document(self, document_id: str) -> None:
        with self._lock:
            self._entries = [
                entry
                for entry in self._entries
                if entry.get("document_id") != document_id
            ]
            self._save()

    def count(self) -> int:
        with self._lock:
            return len(self._entries)
