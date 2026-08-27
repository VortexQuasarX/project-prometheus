// Typed API client. All calls go through the Next.js rewrite (/api/v1) so no
// CORS is needed; the backend also allows direct NEXT_PUBLIC_API_URL access.
import type {
  AgentAction,
  AgentRun,
  ApiError,
  AuditEvent,
  BudgetResponse,
  CacheStats,
  ChatResponse,
  CostReport,
  EvalRunDetail,
  EvalRunSummary,
  HealthResponse,
  KillSwitchMode,
  MetricsResponse,
  Policy,
  TraceDetail,
  TraceListItem,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export function getApiKey(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem("prometheus_api_key") ?? "";
}

export function setApiKey(key: string): void {
  window.localStorage.setItem("prometheus_api_key", key);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-API-Key": getApiKey(),
    "X-Request-Id": crypto.randomUUID(),
    ...(init?.headers as Record<string, string>),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const err = (await res.json()) as ApiError;
      detail = err.error?.message ?? err.detail ?? detail;
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

// --- health / mode probe ----------------------------------------------------
export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function getApiMode(): Promise<"live" | "mock"> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2500);
    const res = await fetch(`${API_BASE}/health`, { signal: controller.signal });
    clearTimeout(timer);
    return res.ok ? "live" : "mock";
  } catch {
    return "mock";
  }
}

// --- chat / ingest ----------------------------------------------------------
export function postChat(body: {
  query: string;
  model?: string;
  provider?: string;
}): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(body) });
}

// --- metrics / cost / cache -------------------------------------------------
export function getMetrics(): Promise<MetricsResponse> {
  return request<MetricsResponse>("/metrics");
}
export function getCostReport(): Promise<CostReport> {
  return request<CostReport>("/cost-report");
}
export function getCacheStats(): Promise<CacheStats> {
  return request<CacheStats>("/cache-stats");
}

// --- traces -----------------------------------------------------------------
export function getTraces(limit = 50): Promise<{ items: TraceListItem[]; total: number }> {
  return request(`/traces?limit=${limit}`);
}
export function getTrace(requestId: string): Promise<TraceDetail> {
  return request<TraceDetail>(`/traces/${encodeURIComponent(requestId)}`);
}

// --- governance -------------------------------------------------------------
export function getPolicies(): Promise<{ policy: Policy; policy_version: number }> {
  return request("/policies");
}
export function putPolicies(policy: Policy, reason: string): Promise<{ policy: Policy; policy_version: number }> {
  return request("/policies", { method: "PUT", body: JSON.stringify({ policy, reason }) });
}
export function getBudget(): Promise<BudgetResponse> {
  return request("/budget");
}
export function setKillSwitch(
  kill_switch_mode: KillSwitchMode,
  reason?: string,
): Promise<{ kill_switch_mode: KillSwitchMode; previous_mode: string }> {
  return request("/budget/kill-switch", {
    method: "POST",
    body: JSON.stringify({ kill_switch_mode, reason }),
  });
}
export function getAlerts(): Promise<{ items: Array<Record<string, unknown>> }> {
  return request("/alerts");
}

// --- agents / approvals -----------------------------------------------------
export function runAgent(body: {
  agent_type: string;
  trigger: string;
  params?: Record<string, unknown>;
}): Promise<AgentRun> {
  return request<AgentRun>("/agents/run", { method: "POST", body: JSON.stringify(body) });
}
export function getAgentRuns(status?: string): Promise<{ items: AgentRun[]; total: number }> {
  const q = status ? `&status=${encodeURIComponent(status)}` : "";
  return request(`/agents/runs?limit=100${q}`);
}
export function getAgentRun(runId: string): Promise<AgentRun> {
  return request<AgentRun>(`/agents/runs/${encodeURIComponent(runId)}`);
}
export function getPendingActions(): Promise<{ items: AgentAction[] }> {
  return request("/agents/actions?status=pending");
}
export function approveAction(actionId: string, note?: string): Promise<AgentAction> {
  return request(`/agents/actions/${encodeURIComponent(actionId)}/approve`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}
export function rejectAction(actionId: string, note?: string): Promise<AgentAction> {
  return request(`/agents/actions/${encodeURIComponent(actionId)}/reject`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

// --- evals / audit / demo ---------------------------------------------------
export function runEvals(): Promise<EvalRunSummary> {
  return request<EvalRunSummary>("/evals/run", { method: "POST", body: JSON.stringify({}) });
}
export function getEvalRuns(): Promise<{ items: EvalRunSummary[]; total: number }> {
  return request("/evals/runs?limit=50");
}
export function getEvalRun(runId: string): Promise<EvalRunDetail> {
  return request<EvalRunDetail>(`/evals/runs/${encodeURIComponent(runId)}`);
}
export function getAudit(limit = 100): Promise<{ items: AuditEvent[]; total: number }> {
  return request(`/audit?limit=${limit}`);
}
export function resetDemo(): Promise<{ status: string }> {
  return request("/demo/reset", { method: "POST", body: JSON.stringify({}) });
}
