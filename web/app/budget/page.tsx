"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { toast } from "sonner";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, ErrorState, Select, Skeleton, statusTone } from "@/components/ui";
import { getBudget, getCostReport, setKillSwitch } from "@/lib/api";
import type { KillSwitchMode } from "@/lib/types";
import { formatUsd } from "@/lib/utils";

export default function BudgetPage() {
  const queryClient = useQueryClient();
  const budget = useQuery({ queryKey: ["budget"], queryFn: getBudget, refetchInterval: 30_000, retry: 0 });
  const cost = useQuery({ queryKey: ["cost-report"], queryFn: getCostReport, refetchInterval: 30_000, retry: 0 });
  const [nextMode, setNextMode] = useState<KillSwitchMode>("off");

  const apply = useMutation({
    mutationFn: () => setKillSwitch(nextMode, "kill switch changed from Budget page"),
    onSuccess: () => {
      toast.success(`Kill switch set to ${nextMode}`);
      void queryClient.invalidateQueries({ queryKey: ["budget"] });
      void queryClient.invalidateQueries({ queryKey: ["audit"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const modelData = (cost.data?.model_wise ?? []).map((m) => ({ name: m.model, cost: Number(m.cost_usd.toFixed(4)) }));
  const dailyBudget = budget.data?.daily_budget_usd ?? 1;
  const dailySpend = budget.data?.daily_spend_usd ?? 0;

  return (
    <PageShell>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Budget state</CardTitle>
            <CardDescription>{formatUsd(dailySpend, 4)} of {formatUsd(dailyBudget, 2)} today · {formatUsd(budget.data?.monthly_spend_usd, 2)} this month</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {budget.isLoading ? <Skeleton className="h-20" /> : (
              <>
                <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={`h-full rounded-full ${dailySpend >= dailyBudget ? "bg-red-600" : dailySpend >= dailyBudget * 0.9 ? "bg-red-400" : dailySpend >= dailyBudget * 0.7 ? "bg-amber-400" : "bg-emerald-500"}`}
                    style={{ width: `${Math.min(100, dailyBudget > 0 ? (dailySpend / dailyBudget) * 100 : 0)}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Status</span>
                  <Badge tone={statusTone(budget.data?.status)}>{budget.data?.status}</Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Kill switch</span>
                  <Badge tone={statusTone(budget.data?.kill_switch_mode)}>{budget.data?.kill_switch_mode}</Badge>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Kill switch control</CardTitle>
            <CardDescription>High-impact: gates every subsequent request</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Select value={nextMode} onChange={(e) => setNextMode(e.target.value as KillSwitchMode)}>
              {["off", "cache_only", "cheap_only", "block_all"].map((m) => <option key={m} value={m}>{m}</option>)}
            </Select>
            <Button
              variant={nextMode === "block_all" ? "destructive" : "default"}
              disabled={apply.isPending || nextMode === budget.data?.kill_switch_mode}
              onClick={() => apply.mutate()}
            >
              {apply.isPending ? "Applying..." : `Set ${nextMode}`}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recommendations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {(budget.data?.recommendations ?? []).slice(0, 4).map((r) => (
              <div key={r.action_id} className="flex items-center justify-between rounded-lg border border-border p-2">
                <span>{r.title}</span>
                <span className="tabular text-xs text-muted-foreground">{formatUsd(r.expected_monthly_saving_usd, 2)}/mo</span>
              </div>
            ))}
            {(budget.data?.recommendations ?? []).length === 0 ? <p className="text-xs text-muted-foreground">No recommendations right now.</p> : null}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Model-wise spend</CardTitle>
          <CardDescription>Where the tokens go</CardDescription>
        </CardHeader>
        <CardContent className="h-64">
          {modelData.length === 0 ? (
            <p className="text-sm text-muted-foreground">No spend recorded yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelData} layout="vertical">
                <XAxis type="number" fontSize={11} tickFormatter={(v: number) => `$${v}`} />
                <YAxis type="category" dataKey="name" fontSize={11} width={110} />
                <Tooltip formatter={(v) => formatUsd(Number(v), 4)} />
                <Bar dataKey="cost" fill="#1d4ed8" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {budget.isError ? <ErrorState message={(budget.error as Error).message} /> : null}
    </PageShell>
  );
}
