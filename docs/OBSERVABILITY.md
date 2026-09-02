# Observability

## Prometheus metrics (VERIFIED locally)

`GET /metrics` (API + ML inference) exposes: `prometheus_requests_total`
(model/decision/cache), `prometheus_request_latency_seconds` histogram,
`prometheus_tokens_total`, `prometheus_cost_usd_total`,
`prometheus_cache_savings_usd_total`, `prometheus_errors_total`,
`prometheus_requests_in_flight`; ML service adds `ml_predictions_total`,
`ml_prediction_latency_seconds`, `ml_model_loaded`.
Test: `tests/test_observability.py`.

## OpenTelemetry (VERIFIED locally — in-process)

`app/observability/metrics.py:start_span` wraps pipeline steps. Exporters:
`OTEL_TRACES_EXPORTER=console|otlp|none` (none = default in tests). OTLP
ships to any collector (Jaeger/Grafana Tempo) at
`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`.

## Grafana (NOT VERIFIED — needs a running Grafana)

Dashboards to build from the metrics above: request rate, error rate, latency
(P95), token usage, cost, cache hit rate, model usage, Kafka consumer lag,
ML inference latency, drift status. JSON dashboards are a V2 deliverable.

## Structured logs + alerts

JSON logging via app.core.logging; alerts: CloudWatch alarms in
`infra/cloudwatch.tf` (budget-critical, error-spike); Grafana alert rules are
V2.
