"""Evaluation harness: golden set, run execution, avg metrics, detail."""

from pathlib import Path
import yaml

EVAL_METRICS = (
    "relevance",
    "groundedness",
    "safety",
    "completeness",
    "cost_efficiency",
    "latency_ms",
    "estimated_cost_usd",
    "cacheability",
)

EXPECTED_CATEGORIES = {
    "cost question",
    "cache question",
    "RAG question",
    "safety question",
    "PII question",
    "complex reasoning question",
    "simple FAQ",
    "unsupported question",
    "prompt injection attempt",
    "repeated cacheable question",
}


def test_golden_prompts_cover_required_categories():
    yaml_path = Path(__file__).resolve().parents[1] / 'evals' / 'golden_prompts.yaml'
    with open(yaml_path, encoding='utf-8') as fh:
        data = yaml.safe_load(fh)
    cases = data["cases"] if isinstance(data, dict) else data
    assert len(cases) >= 10
    categories = {c.get("category") for c in cases}
    missing = EXPECTED_CATEGORIES - categories
    assert not missing, f"missing categories: {missing}"


def test_eval_run_executes_and_scores(client, admin_headers):
    r = client.post("/api/v1/evals/run", json={}, headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_cases"] >= 10
    assert body["passed_cases"] + body["failed_cases"] == body["total_cases"]
    for metric in EVAL_METRICS:
        assert metric in body["avg_metrics"], f"missing avg metric {metric}"


def test_eval_run_persisted_and_listed(client, admin_headers):
    run = client.post("/api/v1/evals/run", json={}, headers=admin_headers).json()
    runs = client.get("/api/v1/evals/runs", headers=admin_headers).json()
    assert any(item["run_id"] == run["run_id"] for item in runs["items"])

    detail = client.get(f"/api/v1/evals/runs/{run['run_id']}", headers=admin_headers)
    assert detail.status_code == 200
    cases = detail.json()["cases"]
    assert len(cases) == run["total_cases"]
    for case in cases:
        assert "passed" in case and "metrics" in case
