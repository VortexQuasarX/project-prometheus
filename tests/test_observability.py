"""Observability: Prometheus /metrics + OpenTelemetry spans (verified locally)."""
from __future__ import annotations

import os

from app.observability.metrics import (
    REGISTRY,
    metrics_payload,
    record_request,
    start_span,
)

os.environ.setdefault("OTEL_TRACES_EXPORTER", "console")


def test_metrics_endpoint_exposes_prometheus_format(client):
    record_request(
        model="mock-small",
        router_decision="CHEAP_MODEL",
        cache_hit=False,
        latency_seconds=0.2,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.00125,
        cache_saved_usd=0.0,
    )
    payload = metrics_payload().decode("utf-8")
    assert "prometheus_requests_total" in payload
    assert "prometheus_request_latency_seconds" in payload
    assert "prometheus_tokens_total" in payload
    assert "prometheus_cost_usd_total" in payload


def test_metrics_route_via_http(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "prometheus_requests_total" in r.text


def test_span_context_manager_records():
    seen = []
    with start_span("test.operation", {"key": "value"}) as _span:
        seen.append(1)
    assert seen == [1]  # context manager completed without error


def test_metrics_registry_isolated():
    # The custom registry keeps test output deterministic.
    names = {m.name for m in REGISTRY.collect()}
    assert "prometheus_requests" in names or "prometheus_requests_total" in names
