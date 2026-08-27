"""RAG pipeline: chunking, retrieval, citations and seed content."""
from __future__ import annotations

from app.rag.chunker import chunk_document, chunk_text
from app.rag.citations import build_citations
from app.rag.retriever import Retriever
from app.rag.seed_content import SEED_DOCUMENTS, ingest_seed_documents

__all__ = [
    "Retriever",
    "SEED_DOCUMENTS",
    "build_citations",
    "chunk_document",
    "chunk_text",
    "ingest_seed_documents",
]
