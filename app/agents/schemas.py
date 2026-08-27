"""Pydantic v2 schemas for the Project Prometheus agent runtime.

These schemas are the wire contract for the agent API endpoints
(``POST /api/v1/agents/run``, ``GET /api/v1/agents/runs``,
``GET /api/v1/agents/runs/{run_id}`` and the approval endpoints).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AgentType = Literal["finops", "reliability", "evaluator", "guardrail", "router"]

# Exact status set from SPEC / DECISIONS B16.
RunStatus = Literal[
    "pending",
    "running",
    "waiting_approval",
    "approved",
    "rejected",
    "applied",
    "verified",
    "failed",
]

APPROVAL_STATUSES = ("none", "pending", "approved", "rejected")


class AgentRunCreate(BaseModel):
    """Request body for POST /api/v1/agents/run."""

    agent_type: AgentType
    trigger: str = Field(..., description="Trigger that started the run")
    params: dict[str, Any] | None = None


class DecisionRequest(BaseModel):
    """Request body for the approve/reject endpoints."""

    note: str | None = None


class AgentActionRecord(BaseModel):
    """An action proposed by an agent (spec example shape)."""

    action_id: str
    title: str
    expected_monthly_saving_usd: float
    risk_level: str
    latency_impact: str
    approval_required: bool
    status: str


class ToolCallRecord(BaseModel):
    """Exact spec shape for a logged tool call."""

    tool: str
    input: dict[str, Any]
    output: dict[str, Any]
    duration_ms: int
    status: str


class StepRecord(BaseModel):
    """One executed pipeline step of an agent run."""

    name: str
    status: str
    input: dict[str, Any]
    output: dict[str, Any]
    duration_ms: int


class RunDetail(BaseModel):
    """Full agent run detail (spec field list, B16)."""

    run_id: str
    agent_type: str
    trigger: str
    status: str
    plan: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    observations: dict[str, Any]
    recommendation: dict[str, Any] | None
    approval_status: str | None
    outcome: Any = None
    created_at: str
    updated_at: str


class RunSummary(BaseModel):
    """List item shape for GET /api/v1/agents/runs."""

    run_id: str
    agent_type: str
    trigger: str
    status: str
    recommendation: dict[str, Any] | None
    expected_saving_usd: float
    created_at: str
    updated_at: str


class RunListResponse(BaseModel):
    items: list[RunSummary]
    total: int
