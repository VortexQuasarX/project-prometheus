"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from "recharts";
import { toast } from "sonner";
import { Target, Play, Shield, Gauge, Zap } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, ErrorState, Skeleton, Table, Td, Th, statusTone } from "@/components/ui";
import { getEvalRun, getEvalRuns, runEvals } from "@/lib/api";
import { formatMs, formatScore, formatTime, formatUsd } from "@/lib/utils";

export default function EvaluationsPage() {
  const queryClient = useQueryClient();
  const runs = useQuery({ queryKey: ["eval-runs"], queryFn: getEvalRuns, retry: 0 });
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useQuery({
    queryKey: ["eval-run", selected],
    queryFn: () => getEvalRun(selected as string),
    enabled: selected !== null,
    retry: 0,
  });

  const trigger = useMutation({
    mutationFn: runEvals,
    onSuccess: (run) => {
      toast.success(`Eval run finished: ${run.passed_cases}/${run.total_cases} passed`);
      void queryClient.invalidateQueries({ queryKey: ["eval-runs"] });
      setSelected(run.run_id);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // Auto-select latest if none selected
  if (!selected && runs.data?.items && runs.data.items.length > 0) {
    setSelected(runs.data.items[0].run_id);
  }

  const latest = runs.data?.items?.find(r => r.run_id === selected) ?? runs.data?.items?.[0];
  const radarData = latest
    ? [
        { dim: "Relevance", score: latest.avg_metrics.relevance ?? 0 },
        { dim: "Groundedness", score: latest.avg_metrics.groundedness ?? 0 },
        { dim: "Safety", score: latest.avg_metrics.safety ?? 0 },
        { dim: "Completeness", score: latest.avg_metrics.completeness ?? 0 },
        { dim: "Cost Eff.", score: latest.avg_metrics.cost_efficiency ?? 0 },
      ]
    : [];

  return (
    <PageShell>
      <Card className="mb-6">
        <CardHeader className="flex-row items-center justify-between space-y-0 border-b border-border/50 bg-muted/10">
          <div>
            <CardTitle className="flex items-center gap-2"><Target size={20} className="text-accent" /> Evaluation Harness</CardTitle>
            <CardDescription>Golden-set scoring across 5 key dimensions</CardDescription>
          </div>
          <Button disabled={trigger.isPending} onClick={() => trigger.mutate()} className="shadow-lg gap-2">
            <Play size={16} /> {trigger.isPending ? "Evaluating..." : "Run Evals"}
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {runs.isLoading ? (
            <Skeleton className="h-40" />
          ) : runs.isError ? (
            <div className="p-6"><ErrorState message={(runs.error as Error).message} /></div>
          ) : (runs.data?.items ?? []).length === 0 ? (
            <EmptyState title="No evaluation history" hint="Run the harness against the golden dataset to score models." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    <Th>Run ID</Th>
                    <Th className="text-center">Pass Rate</Th>
                    <Th className="text-right">Avg Overall</Th>
                    <Th className="text-right">Avg Cost</Th>
                    <Th className="text-right">Avg Latency</Th>
                    <Th>Executed</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {(runs.data?.items ?? []).map((r) => {
                    const isSelected = selected === r.run_id;
                    const passPct = r.total_cases > 0 ? r.passed_cases / r.total_cases : 0;
                    return (
                      <tr
                        key={r.run_id}
                        className={`cursor-pointer transition-colors ${isSelected ? "bg-accent/10 hover:bg-accent/15" : "hover:bg-muted/30"}`}
                        onClick={() => setSelected(r.run_id)}
                      >
                        <Td className="font-mono text-xs">
                          <span className={isSelected ? "text-accent font-bold" : ""}>{r.run_id.split('-')[0]}</span>
                        </Td>
                        <Td>
                          <div className="flex flex-col items-center gap-1">
                            <span className="text-xs font-semibold">{r.passed_cases}/{r.total_cases}</span>
                            <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                              <div className={`h-full ${passPct >= 0.8 ? 'bg-emerald-500' : passPct >= 0.5 ? 'bg-amber-500' : 'bg-red-500'}`} style={{ width: `${passPct * 100}%` }} />
                            </div>
                          </div>
                        </Td>
                        <Td className="tabular text-right font-bold">{formatScore(r.avg_metrics.overall ?? null)}</Td>
                        <Td className="tabular text-right text-xs text-muted-foreground">{formatUsd(r.avg_metrics.estimated_cost_usd ?? 0)}</Td>
                        <Td className="tabular text-right text-xs text-muted-foreground">{formatMs(r.avg_metrics.latency_ms ?? 0)}</Td>
                        <Td className="text-[11px] text-muted-foreground">{formatTime(r.created_at)}</Td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {selected && detail.isLoading ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3"><Skeleton className="h-[400px]" /><Skeleton className="h-[400px] lg:col-span-2" /></div>
      ) : selected && detail.data ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 animate-fade-in-up">
          <Card className="flex flex-col bg-background/50">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2"><Gauge size={16} className="text-accent" /> Dimension Radar</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 h-64 min-h-[300px] flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} outerRadius="70%">
                  <PolarGrid stroke="hsl(var(--border))" />
                  <PolarAngleAxis dataKey="dim" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10, fontWeight: 600 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '0.75rem', fontSize: '12px' }}
                  />
                  <Radar dataKey="score" stroke="hsl(var(--accent))" strokeWidth={2} fill="hsl(var(--accent))" fillOpacity={0.2} />
                </RadarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2 flex flex-col bg-background/50">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle className="text-base flex items-center gap-2"><Shield size={16} className="text-emerald-500" /> Case Breakdown</CardTitle>
              </div>
              <Badge tone={detail.data.passed_cases === detail.data.total_cases ? "green" : "amber"}>
                {((detail.data.passed_cases / detail.data.total_cases) * 100).toFixed(0)}% pass rate
              </Badge>
            </CardHeader>
            <CardContent className="p-0 overflow-hidden rounded-b-xl flex-1">
              <div className="max-h-[400px] overflow-y-auto">
                <table className="w-full text-sm text-left whitespace-nowrap">
                  <thead className="sticky top-0 bg-muted/80 backdrop-blur z-10 text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                    <tr><th className="px-4 py-2">Case</th><th className="px-4 py-2">Category</th><th className="px-4 py-2">Result</th><th className="px-4 py-2 text-right">Score</th><th className="px-4 py-2 text-right">Cost</th></tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {detail.data.cases.map((c, i) => (
                      <tr key={`${c.case_id}-${i}`} className="hover:bg-muted/30">
                        <td className="px-4 py-3 font-mono text-[11px] font-semibold">{c.case_id}</td>
                        <td className="px-4 py-3 text-xs">
                          <span className="bg-muted px-2 py-0.5 rounded text-muted-foreground">{c.category ?? "—"}</span>
                        </td>
                        <td className="px-4 py-3">
                          <div className={`w-2.5 h-2.5 rounded-full ${c.passed ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]'}`} title={c.passed ? "Pass" : "Fail"} />
                        </td>
                        <td className="px-4 py-3 tabular text-right font-medium">{formatScore(c.metrics?.overall ?? null)}</td>
                        <td className="px-4 py-3 tabular text-right text-xs text-muted-foreground">{formatUsd(c.cost_usd ?? 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </PageShell>
  );
}
