// Shared data contracts mirroring the FastAPI backend (app/api/v1).

export type RouterDecision =
  | "CACHE_ONLY"
  | "CHEAP_MODEL"
  | "STRONG_MODEL"
  | "GUARDRAIL_REVIEW"
  | "REJECT"
  | "CLARIFY";

export type KillSwitchMode = "off" | "cache_only" | "cheap_only" | "block_all";
export type BudgetState = "normal" | "warning" | "critical" | "exceeded";
export type AgentRunStatus =
  | "pending"
  | "running"
  | "waiting_approval"
  | "approved"
  | "rejected"
  | "applied"
  | "verified"
  | "failed";

export interface Citation {
  document_id: string;
  title: string;
  chunk_id: string;
  snippet: string;
}

export interface ChatResponse {
  request_id: string;
  answer: string;
  provider: string;
  model: string;
  router_decision: RouterDecision;
  cache_hit: boolean;
  estimated_cost_usd: number;
  cost_saved_usd: number;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  guardrail_status: string;
  evaluation_score: number | null;
  citations: Citation[];
  trace_url: string;
}

export interface Recommendation {
  action_id: string;
  title: string;
  expected_monthly_saving_usd: number;
  risk_level: string;
  latency_impact: string;
  approval_required: boolean;
  status: string;
}

export interface BudgetResponse {
  daily_spend_usd: number;
  monthly_spend_usd: number;
  daily_budget_usd: number;
  status: BudgetState;
  kill_switch_mode: KillSwitchMode;
  recommendations: Recommendation[];
}

export interface Policy {
  daily_budget_usd: number;
  request_budget_usd: number;
  max_input_tokens: number;
  max_output_tokens: number;
  allowed_models: string[];
  expensive_models?: string[];
  expensive_model_limit_per_day: number;
  require_cache_check: boolean;
  require_rag: boolean;
  require_evaluation: boolean;
  require_human_approval: boolean;
  pii_masking_enabled: boolean;
  prompt_injection_detection_enabled: boolean;
  rate_limit_per_minute: number;
  kill_switch_mode: KillSwitchMode;
  [key: string]: unknown;
}

export interface ToolCall {
  tool: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  duration_ms: number;
  status: string;
}

export interface AgentAction {
  action_id: string;
  title: string;
  expected_monthly_saving_usd: number;
  risk_level: string;
  latency_impact: string;
  approval_required: boolean;
  status: string;
  run_id?: string;
}

export interface AgentRun {
  run_id: string;
  agent_type: string;
  trigger: string;
  status: AgentRunStatus;
  plan: Array<Record<string, unknown>> | string[];
  steps: Array<Record<string, unknown>>;
  tool_calls: ToolCall[];
  observations: Record<string, unknown> | unknown[];
  recommendation: Record<string, unknown> | string | null;
  approval_status: string;
  outcome: Record<string, unknown> | string | null;
  expected_saving_usd?: number;
  created_at: string;
  updated_at: string;
}

export interface TraceEvent {
  request_id: string;
  name: string;
  status: string;
  duration_ms: number;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface TraceListItem {
  request_id: string;
  status: string;
  model: string | null;
  provider: string | null;
  router_decision: string | null;
  cache_hit: boolean;
  cost_usd: number;
  latency_ms: number;
  created_at: string;
}

export interface TraceDetail {
  request_id: string;
  status: string;
  created_at: string;
  timeline: TraceEvent[];
  summary: Record<string, unknown>;
}

export interface EvalRunSummary {
  run_id: string;
  status: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  avg_metrics: Record<string, number>;
  created_at: string;
}

export interface EvalCase {
  case_id: string;
  category?: string;
  prompt?: string;
  passed: boolean;
  metrics: Record<string, number>;
  latency_ms: number;
  cost_usd: number;
  feedback?: string;
}

export interface EvalRunDetail extends EvalRunSummary {
  cases: EvalCase[];
}

export interface AuditEvent {
  event_id: string;
  actor: string;
  role: string;
  action: string;
  resource: string;
  request_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Alert {
  id: number;
  alert_type: string;
  severity: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface MetricsResponse {
  total_requests: number;
  total_cost_usd: number;
  cache_hit_rate: number;
  avg_latency_ms: number;
  budget_status: BudgetState;
  kill_switch_mode: KillSwitchMode;
  recent_alerts: Alert[];
  pending_approvals: number;
  top_recommendations: Recommendation[];
  requests_last_24h?: Array<Record<string, unknown>>;
  failed_requests?: number;
  model_usage?: Array<Record<string, unknown>>;
}

export interface ModelSpend {
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  requests: number;
}

export interface CostReport {
  daily: Array<{ date: string; cost: number }>;
  monthly: Array<{ month: string; cost: number }>;
  model_wise: ModelSpend[];
  total_spend_usd: number;
  cache_savings_usd: number;
  recommendations: Recommendation[];
  trend?: Array<{ date: string; cost: number }>;
}

export interface CacheStats {
  hit_count: number;
  miss_count: number;
  hit_rate: number;
  entry_count: number;
  total_cost_saved_usd: number;
  threshold: number;
  ttl_seconds: number;
  policy_version: number;
  kb_version: number;
  cache_version: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  db: string;
}

export interface ApiError {
  request_id?: string;
  error?: { code: string; message: string; details?: unknown };
  detail?: string;
}
