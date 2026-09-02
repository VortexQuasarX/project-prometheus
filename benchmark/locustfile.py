"""Locust load test for the Prometheus API.

Run headless:
    locust -f benchmark/locustfile.py --headless -u 20 -r 5 -t 60s \
           --host http://localhost:8000 --only-summary --csv benchmark/results

Env: PROM_API_KEY (default prometheus-demo-admin-key).
"""
from __future__ import annotations

import os
import random

from locust import HttpUser, between, task

QUERIES = [
    "What is AI cost governance?",
    "Explain semantic caching for LLM gateways",
    "What are AWS Bedrock cost controls?",
    "Compare dense and hybrid retrieval for enterprise RAG",
    "How do guardrails protect against prompt injection?",
]


class PrometheusUser(HttpUser):
    wait_time = between(0.2, 1.0)

    def on_start(self) -> None:
        self.key = os.environ.get("PROM_API_KEY", "prometheus-demo-admin-key")
        self.client.headers.update({"X-API-Key": self.key})

    @task(6)
    def chat(self) -> None:
        self.client.post(
            "/api/v1/chat",
            json={"query": random.choice(QUERIES)},
            name="POST /chat",
        )

    @task(2)
    def metrics(self) -> None:
        self.client.get("/api/v1/metrics", name="GET /metrics")

    @task(1)
    def cache_stats(self) -> None:
        self.client.get("/api/v1/cache-stats", name="GET /cache-stats")

    @task(1)
    def health(self) -> None:
        self.client.get("/api/v1/health", name="GET /health")
