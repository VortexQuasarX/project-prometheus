"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer } from "recharts";
import { toast } from "sonner";
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

  const latest = runs.data?.items?.[0];
  const radarData = latest
    ? [
        { dim: "relevance", score: latest.avg_metrics.relevance ?? 0 },
        { dim: "groundedness", score: latest.avg_metrics.groundedness ?? 0 },
        { dim: "safety", score: latest.avg_metrics.safety ?? 0 },
        { dim: "completeness", score: latest.avg_metrics.completeness ?? 0 },
        { dim: "cost eff.", score: latest.avg_metrics.cost_efficiency ?? 0 },
      ]
    : [];

  return (
    <PageShell>
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Evaluation runs</CardTitle>
            <CardDescription>Golden-set scoring across relevance, grounding, safety, completeness, cost</CardDescription>
          </div>
          <Button size="sm" disabled={trigger.isPending} onClick={() => trigger.mutate()}>
            {trigger.isPending ? "Running..." : "Run evaluation"}
          </Button>
        </CardHeader>
        <CardContent>
          {runs.isLoading ? (
            <Skeleton className="h-40" />
          ) : runs.isError ? (
            <ErrorState message={(runs.error as Error).message} />
          ) : (runs.data?.items ?? []).length === 0 ? (
            <EmptyState title="No eval runs yet" hint="Run the harness above." />
          ) : (
            <Table>
              <thead>
                <tr><Th>Run</Th><Th className="text-right">Passed</Th><Th className="text-right">Avg overall</Th><Th className="text-right">Avg cost</Th><Th className="text-right">Avg latency</Th><Th>Created</Th></tr>
              </thead>
              <tbody>
                {(runs.data?.items ?? []).map((r) => (
                  <tr
                    key={r.run_id}
                    className={`cursor-pointer border-t border-border hover:bg-muted/40 ${selected === r.run_id ? "bg-muted/40" : ""}`}
                    onClick={() => setSelected(r.run_id)}
                  >
                    <Td className="font-mono text-xs">{r.run_id}</Td>
                    <Td className="tabular text-right">{r.passed_cases}/{r.total_cases}</Td>
                    <Td className="tabular text-right">{formatScore(r.avg_metrics.overall ?? null)}</Td>
                    <Td className="tabular text-right">{formatUsd(r.avg_metrics.estimated_cost_usd ?? 0)}</Td>
                    <Td className="tabular text-right">{formatMs(r.avg_metrics.latency_ms ?? 0)}</Td>
                    <Td className="text-xs text-muted-foreground">{formatTime(r.created_at)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </CardContent>
      </Card>

      {selected && detail.data ? (
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Average dimension scores</CardTitle>
              <CardDescription>{detail.data.run_id}</CardDescription>
            </CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="dim" fontSize={10} />
                  <Radar dataKey="score" stroke="#1d4ed8" fill="#1d4ed8" fillOpacity={0.4} />
                </RadarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Per-case results</CardTitle>
              <CardDescription>{detail.data.passed_cases}/{detail.data.total_cases} passed</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <thead><tr><Th>Case</Th><Th>Category</Th><Th>Passed</Th><Th className="text-right">Score</Th><Th className="text-right">Cost</Th></tr></thead>
                <tbody>
                  {detail.data.cases.map((c, i) => (
                    <tr key={`${c.case_id}-${i}`} className="border-t border-border">
                      <Td className="font-mono text-xs">{c.case_id}</Td>
                      <Td className="text-xs">{c.category ?? "—"}</Td>
                      <Td><Badge tone={c.passed ? "green" : "red"}>{c.passed ? "pass" : "fail"}</Badge></Td>
                      <Td className="tabular text-right">{formatScore(c.metrics?.overall ?? null)}</Td>
                      <Td className="tabular text-right">{formatUsd(c.cost_usd ?? 0)}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </PageShell>
  );
}
