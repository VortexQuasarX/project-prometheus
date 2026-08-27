"""Cost model: pricing constants, formula, budget states, kill-switch escalation."""

from app.cost.pricing import MODEL_PRICING, estimate_cost
from app.cost.tracker import get_model_wise_spend, record_usage
from app.governance.budget import after_spend_recorded, compute_state, get_budget_status

EXPECTED_PRICING = {
    "mock-small": (0.0050, 0.0150, 0.0010, 0.0020),
    "mock-large": (0.0200, 0.0600, 0.0040, 0.0080),
    "bedrock-cheap": (0.0030, 0.0150, 0.0010, 0.0020),
    "bedrock-strong": (0.0300, 0.1500, 0.0030, 0.0060),
}

FIELDS = (
    "input_cost_per_1k_tokens",
    "output_cost_per_1k_tokens",
    "cache_read_cost_per_1k_tokens",
    "cache_write_cost_per_1k_tokens",
)


def test_pricing_table_numbers():
    for model, expected in EXPECTED_PRICING.items():
        pricing = MODEL_PRICING[model]
        for field, value in zip(FIELDS, expected, strict=False):
            assert abs(pricing[field] - value) < 1e-9, f"{model}.{field}"


def test_estimate_cost_formula():
    # mock-small: 1000 in * 0.005/1k + 500 out * 0.015/1k = 0.005 + 0.0075
    assert abs(estimate_cost("mock-small", 1000, 500) - 0.0125) < 1e-9
    # mock-large: 1000 * 0.02/1k + 500 * 0.06/1k = 0.02 + 0.03
    assert abs(estimate_cost("mock-large", 1000, 500) - 0.05) < 1e-9
    # cache-write leg adds cache_write rate on the written tokens
    with_cache_write = estimate_cost("mock-small", 1000, 0, cache_write_tokens=1000)
    assert abs(with_cache_write - (0.005 + 0.002)) < 1e-9


def test_budget_state_transitions():
    # daily budget default 2.0: warning >= 70% (1.4), critical >= 90% (1.8), exceeded >= 100% (2.0)
    assert compute_state(0.0) == "normal"
    assert compute_state(1.0) == "normal"
    assert compute_state(1.4) == "warning"
    assert compute_state(1.8) == "critical"
    assert compute_state(2.0) == "exceeded"


def test_budget_escalation_on_exceeded():
    record_usage("cost-test-1", "mock-large", "mock", 1000, 500, cost_usd=1.5)
    after_spend_recorded()
    assert get_budget_status()["status"] == "warning"
    record_usage("cost-test-2", "mock-large", "mock", 1000, 500, cost_usd=0.35)
    after_spend_recorded()
    assert get_budget_status()["status"] == "critical"
    record_usage("cost-test-3", "mock-large", "mock", 1000, 500, cost_usd=0.2)
    after_spend_recorded()
    status = get_budget_status()
    assert status["status"] == "exceeded"
    # exceeded escalates the kill switch per policy (auto cheap_only, B7)
    assert status["kill_switch_mode"] == "cheap_only"
    model_wise = {m["model"]: m["cost_usd"] for m in get_model_wise_spend()}
    assert "mock-large" in model_wise
