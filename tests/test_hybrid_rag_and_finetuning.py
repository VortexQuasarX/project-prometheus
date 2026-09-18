"""Tests for Group 2 Upgrades: Hybrid Search (BM25 + CrossEncoder), Kafka Event Bus, and LoRA Fine-Tuning."""
from __future__ import annotations

import json
import pytest

from app.rag.bm25 import BM25Index
from app.rag.reranker import CrossEncoderReRanker
from app.rag.retriever import Retriever
from app.events_pipeline.kafka_pipeline import (
    publish_telemetry_event,
    get_kafka_telemetry_status,
    TOPIC_REQUESTS,
    TOPIC_AUDIT,
)
from app.ml.fine_tuning import (
    curate_golden_dataset,
    export_dataset_jsonl,
    generate_lora_config,
    generate_sft_training_script,
)


def test_bm25_sparse_retrieval():
    corpus = [
        {"content": "FinOps for AI models requires granular token accounting and cost tracking.", "title": "FinOps"},
        {"content": "Kafka is an asynchronous distributed streaming platform for high-throughput event ingestion.", "title": "Kafka"},
        {"content": "Parameter-efficient fine-tuning with LoRA freezes pre-trained model weights and injects low-rank matrices.", "title": "LoRA"},
    ]
    index = BM25Index()
    index.fit(corpus)
    results = index.search("token accounting FinOps", top_k=2)
    assert len(results) > 0
    top_chunk, top_score = results[0]
    assert top_chunk["title"] == "FinOps"
    assert top_score > 0


def test_cross_encoder_reranker():
    query = "What is LoRA parameter-efficient fine-tuning?"
    candidates = [
        {"content": "Kubernetes horizontal pod autoscaling adjusts replica counts based on CPU utilization.", "title": "K8s"},
        {"content": "LoRA (Low-Rank Adaptation) freezes weights and injects trainable rank-decomposition matrices into Transformer layers.", "title": "LoRA"},
        {"content": "Kafka broker partitions handle distributed event delivery across consumer groups.", "title": "Kafka"},
    ]
    reranker = CrossEncoderReRanker()
    scored = reranker.rerank(query, candidates, top_k=2)
    assert len(scored) == 2
    # Candidate with title "LoRA" must be ranked first
    assert scored[0]["title"] == "LoRA"
    assert scored[0]["rerank_score"] > scored[1]["rerank_score"]


def test_hybrid_search_retriever():
    class MockEmbedder:
        def embed(self, texts):
            return [[0.1] * 128 for _ in texts]

    class MockVectorStore:
        def __init__(self):
            self._entries = [
                {
                    "chunk_id": "c1",
                    "document_id": "doc1",
                    "content": "FinOps token accounting policy for AI models",
                    "score": 0.88,
                    "metadata": {"title": "FinOps Policy"},
                },
                {
                    "chunk_id": "c2",
                    "document_id": "doc2",
                    "content": "Kafka asynchronous event streaming architecture",
                    "score": 0.45,
                    "metadata": {"title": "Kafka Architecture"},
                },
            ]

        def search(self, embedding, top_k=5):
            return self._entries[:top_k]

    retriever = Retriever(get_db=None, embedder=MockEmbedder(), vector_store=MockVectorStore())
    results = retriever.retrieve(query="FinOps token accounting", top_k=2, mode="hybrid")
    assert len(results) > 0
    top = results[0]
    assert "score" in top
    assert "dense_score" in top
    assert "bm25_score" in top
    assert "rerank_score" in top
    assert top["document_id"] == "doc1"


def test_kafka_pipeline_and_telemetry():
    status = get_kafka_telemetry_status()
    assert "broker_type" in status
    assert "topics" in status
    assert len(status["topics"]) >= 3

    # Test publishing event (fire-and-forget without throwing)
    publish_telemetry_event(TOPIC_REQUESTS, {"request_id": "test_req", "cost": 0.001})


def test_lora_fine_tuning_pipeline():
    dataset = curate_golden_dataset(min_score=0.8, limit=10)
    assert len(dataset) > 0
    assert "query" in dataset[0]
    assert "answer" in dataset[0]

    # Test ChatML JSONL export
    chatml_jsonl = export_dataset_jsonl(dataset, output_format="chatml")
    lines = [line for line in chatml_jsonl.strip().split("\n") if line]
    assert len(lines) > 0
    parsed = json.loads(lines[0])
    assert "messages" in parsed

    # Test Alpaca JSONL export
    alpaca_jsonl = export_dataset_jsonl(dataset, output_format="alpaca")
    lines_alpaca = [line for line in alpaca_jsonl.strip().split("\n") if line]
    assert len(lines_alpaca) > 0
    parsed_alpaca = json.loads(lines_alpaca[0])
    assert "instruction" in parsed_alpaca
    assert "output" in parsed_alpaca

    # Test LoRA config generator
    cfg = generate_lora_config(r=16, lora_alpha=32)
    assert cfg["r"] == 16
    assert cfg["lora_alpha"] == 32
    assert "q_proj" in cfg["target_modules"]

    # Test training script generation
    script = generate_sft_training_script(base_model="meta-llama/Meta-Llama-3-8B-Instruct")
    assert "SFTTrainer" in script
    assert "LoraConfig" in script
