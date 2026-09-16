import { motion } from "framer-motion";
"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";
import { Bot, Play, Cpu, ArrowRight, Shield } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, ErrorState, Skeleton, Table, Td, Th, statusTone } from "@/components/ui";
import { getAgentRuns, runAgent } from "@/lib/api";
import { formatTime, formatUsd } from "@/lib/utils";

export default function AgentsPage() {
  const runs = useQuery({ queryKey: ["agent-runs"], queryFn: () => getAgentRuns(), refetchInterval: 15_000, retry: 0 });
  
  const trigger = useMutation({
    mutationFn: () => runAgent({ agent_type: "finops", trigger: "manual" }),
    onSuccess: () => {
      toast.success("FinOps agent run created and executing...");
      void runs.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <PageShell>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Bot size={20} className="text-accent" /> Autonomous Agents</CardTitle>
            <CardDescription>Multi-agent orchestration for governance and FinOps</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* FinOps Agent Card */}
              <div className="border border-border/50 rounded-xl bg-background/50 p-4 relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent pointer-events-none" />
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-emerald-500/10 text-emerald-500 rounded-lg"><Cpu size={16} /></div>
                  <h3 className="font-bold text-sm">FinOps Optimizer</h3>
                </div>
                <p className="text-xs text-muted-foreground mb-4 h-8 leading-relaxed">Analyzes telemetry, simulates routing rules, and proposes cost-saving policy changes.</p>
                <Button size="sm" className="w-full gap-2 shadow-sm" disabled={trigger.isPending} onClick={() => trigger.mutate()}>
                  <Play size={14} /> {trigger.isPending ? "Executing..." : "Manual Run"}
                </Button>
              </div>

              <div className="border border-border/50 rounded-xl bg-background/50 p-4 relative overflow-hidden hover:bg-background/80 transition-colors">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-red-500/10 text-red-500 rounded-lg"><Shield size={16} /></div>
                  <h3 className="font-bold text-sm">Red Team Agent</h3>
                </div>
                <p className="text-xs text-muted-foreground mb-4 h-8 leading-relaxed">Continuously probes the API for prompt injection vulnerabilities.</p>
                <Link href="/redteam" className="w-full">
                  <Button size="sm" className="w-full bg-red-600 hover:bg-red-700 text-white shadow-lg">
                    <Play size={14} className="mr-2" /> Launch Simulation
                  </Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Global Agent Stats */}
        <Card className="bg-muted/10">
          <CardHeader>
            <CardTitle>Fleet Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Active Runs</span>
              <span className="font-mono font-bold text-accent">
                {(runs.data?.items ?? []).filter(r => r.status === "running" || r.status === "pending").length}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Pending Approvals</span>
              <span className="font-mono font-bold text-amber-500">
                {(runs.data?.items ?? []).filter(r => r.status === "waiting_approval").length}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Total Execution</span>
              <span className="font-mono font-bold">
                {(runs.data?.items ?? []).length}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="border-b border-border/50 bg-muted/5">
          <CardTitle>Execution Log</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {runs.isLoading ? (
            <div className="p-6"><Skeleton className="h-40" /></div>
          ) : runs.isError ? (
            <div className="p-6"><ErrorState message={(runs.error as Error).message} /></div>
          ) : (runs.data?.items ?? []).length === 0 ? (
            <EmptyState title="No agent runs yet" hint="Trigger the FinOps agent to see execution traces." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm whitespace-nowrap">
                <thead>
                  <tr>
                    <Th>Run ID</Th>
                    <Th>Agent</Th>
                    <Th>Trigger</Th>
                    <Th>Status</Th>
                    <Th>Result</Th>
                    <Th className="text-right">Projected Value</Th>
                    <Th>Time</Th>
                    <Th className="text-right">Actions</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {(runs.data?.items ?? []).map((r) => (
                    <tr key={r.run_id} className="hover:bg-muted/30 transition-colors group">
                      <Td className="font-mono text-[11px] font-semibold">{r.run_id.split('-')[0]}...</Td>
                      <Td>
                        <Badge tone="gray" className="bg-background">{r.agent_type}</Badge>
                      </Td>
                      <Td className="text-xs text-muted-foreground">{r.trigger}</Td>
                      <Td>
                        <Badge tone={statusTone(r.status)} className={r.status === "running" ? "animate-pulse" : ""}>
                          {r.status}
                        </Badge>
                      </Td>
                      <Td className="max-w-[200px] truncate text-xs">
                        {r.status === "running" ? (
                          <span className="italic text-muted-foreground">thinking...</span>
                        ) : typeof r.recommendation === "string" ? (
                          r.recommendation
                        ) : (
                          String((r.recommendation as Record<string, unknown> | null)?.title ?? "—")
                        )}
                      </Td>
                      <Td className="tabular text-right font-semibold text-emerald-500">
                        {r.expected_saving_usd ? formatUsd(r.expected_saving_usd, 2) : "—"}
                      </Td>
                      <Td className="text-[10px] text-muted-foreground">{formatTime(r.created_at)}</Td>
                      <Td className="text-right">
                        <Link href={`/agents/runs/${r.run_id}`}>
                          <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                            <ArrowRight size={14} />
                          </Button>
                        </Link>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </PageShell>
  );
}


