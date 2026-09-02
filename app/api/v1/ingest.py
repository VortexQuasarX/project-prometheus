"""POST /api/v1/ingest — document ingestion (chunk -> embed -> store)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.rbac import require_permission
from app.db.session import get_db
from app.governance.audit import append as audit_append
from app.providers.embeddings.base import get_embedder
from app.rag.retriever import Retriever
from app.vector.base import get_vector_store

router = APIRouter()


class IngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=200_000)
    document_id: str | None = Field(default=None, max_length=64)
    metadata: dict | None = None


@router.post("/ingest")
def ingest(
    body: IngestRequest,
    key: object = Depends(require_permission("documents:write")),
    db: Session = Depends(get_db),
) -> dict:
    """Chunk + embed + store a document; bumps the KB version (cache invalidation)."""
    retriever = Retriever(lambda: db, get_embedder(), get_vector_store())
    document_id = body.document_id or f"doc_{uuid.uuid4().hex[:8]}"
    result = retriever.ingest(
        document_id, body.title, body.content, metadata=body.metadata
    )
    audit_append(
        getattr(key, "name", "admin") or "admin",
        getattr(key, "role", "admin") or "admin",
        "document.ingested",
        result.get("document_id", document_id),
        metadata={"title": body.title, "chunks_created": result.get("chunks_created")},
    )
    return result
