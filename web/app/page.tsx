"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { PageShell } from "@/components/page-shell";
import { Badge, Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, MetricCard, Progress, Skeleton, statusTone, Table, Td, Th } from "@/components/ui";
import { getBudget, getCacheStats, getCostReport, getMetrics, getPendingActions } from "@/lib/api";
import { formatMs, formatPercent, formatUsd } from "@/lib/utils";

export default function DashboardPage() {
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: getMetrics, refetchInterval: 30_000, retry: 0 });
  const cost = useQuery({ queryKey: ["cost-report"], queryFn: getCostReport, refetchInterval: 30_000, retry: 0 });
  const cache = useQuery({ queryKey: ["cache-stats"], queryFn: getCacheStats, refetchInterval: 30_000, retry: 0 });
  const budget = useQuery({ queryKey: ["budget"], queryFn: getBudget, refetchInterval: 30_000, retry: 0 });
  const pending = useQuery({ queryKey: ["pending-actions"], queryFn: getPendingActions, refetchInterval: 20_000, retry: 0 });

  const modelData = (cost.data?.model_wise ?? []).map((m) => ({ name: m.model, cost: Number(m.cost_usd.toFixed(4)) }));
  const dailyBudget = budget.data?.daily_budget_usd ?? 1;
  const dailySpend = budget.data?.daily_spend_usd ?? 0;

  return (
    <PageShell>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)
        ) : metrics.isError ? (
          <div className="sm:col-span-2 xl:col-span-4"><EmptyState title="Backend offline" hint="Start the API with `make api` — showing what we can." /></div>
        ) : (
          <>
            <MetricCard label="Total requests" value={metrics.data?.total_requests ?? 0} sub={`${metrics.data?.failed_requests ?? 0} failed`} />
            <MetricCard label="Total cost" value={formatUsd(metrics.data?.total_cost_usd, 4)} sub={`cache saved ${formatUsd(cost.data?.cache_savings_usd, 4)}`} />
            <MetricCard label="Cache hit rate" value={formatPercent(metrics.data?.cache_hit_rate)} sub={`${cache.data?.entry_count ?? 0} entries`} />
            <MetricCard label="Avg latency" value={formatMs(metrics.data?.avg_latency_ms)} />
          </>
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Budget usage</CardTitle>
            <CardDescription>
              {budget.data ? `${formatUsd(dailySpend, 4)} of ${formatUsd(dailyBudget, 2)} daily` : "—"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {budget.isLoading ? <Skeleton className="h-8" /> : (
              <>
                <Progress value={dailyBudget > 0 ? dailySpend / dailyBudget : 0} />
                <div className="flex items-center justify-between text-xs">
                  <span>Monthly: {formatUsd(budget.data?.monthly_spend_usd, 2)}</span>
                  <Badge tone={statusTone(budget.data?.status)}>{budget.data?.status}</Badge>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span>Kill switch</span>
                  <Badge tone={statusTone(budget.data?.kill_switch_mode)}>{budget.data?.kill_switch_mode}</Badge>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Model-wise spend</CardTitle>
            <CardDescription>Accumulated cost per model</CardDescription>
          </CardHeader>
          <CardContent className="h-56">
            {modelData.length === 0 ? (
              <EmptyState title="No spend recorded yet" hint="Run a few playground queries." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={modelData}>
                  <XAxis dataKey="name" fontSize={11} />
                  <YAxis fontSize={11} tickFormatter={(v: number) => `$${v}`} />
                  <Tooltip formatter={(v) => formatUsd(Number(v), 4)} />
                  <Bar dataKey="cost" fill="#1d4ed8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Pending approvals</CardTitle>
            <CardDescription>FinOps actions waiting for a human</CardDescription>
          </CardHeader>
          <CardContent>
            {(pending.data?.items ?? []).length === 0 ? (
              <EmptyState title="No pending approvals" />
            ) : (
              <Table>
                <thead><tr><Th>Action</Th><Th>Saving</Th><Th>Risk</Th></tr></thead>
                <tbody>
                  {(pending.data?.items ?? []).map((a) => (
                    <tr key={a.action_id} className="border-t border-border">
                      <Td><Link className="text-accent hover:underline" href="/approvals">{a.title}</Link></Td>
                      <Td className="tabular">{formatUsd(a.expected_monthly_saving_usd, 2)}</Td>
                      <Td><Badge tone={statusTone(a.risk_level === "low" ? "normal" : "critical")}>{a.risk_level}</Badge></Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top cost recommendations</CardTitle>
            <CardDescription>Generated from live usage telemetry</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {(budget.data?.recommendations ?? []).slice(0, 3).map((r) => (
              <div key={r.action_id} className="flex items-center justify-between rounded-lg border border-border p-2 text-sm">
                <span>{r.title}</span>
                <span className="tabular text-xs text-muted-foreground">{formatUsd(r.expected_monthly_saving_usd, 2)}/mo</span>
              </div>
            ))}
            {(budget.data?.recommendations ?? []).length === 0 ? <EmptyState title="No recommendations right now" /> : null}
          </CardContent>
        </Card>
      </div>
    </PageShell>
  );
}
