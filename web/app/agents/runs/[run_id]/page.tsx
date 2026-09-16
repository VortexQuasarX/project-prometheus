import { motion } from "framer-motion";
"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Cpu, Terminal, FileCode2, Sparkles, CheckCircle2 } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Card, CardContent, CardHeader, CardTitle, ErrorState, JsonViewer, Skeleton, statusTone } from "@/components/ui";
import { getAgentRun } from "@/lib/api";
import { formatMs, formatTime } from "@/lib/utils";
import { AgentRunDAG } from "@/components/AgentRunDAG";
import { useState } from "react";

export default function AgentRunDetailPage() {
  const params = useParams<{ run_id: string }>();
  const runId = params.run_id as string;
  const [viewMode, setViewMode] = useState<"dag" | "list">("dag");
  const run = useQuery({ queryKey: ["agent-run", runId], queryFn: () => getAgentRun(runId), retry: 0 });

  let body = <div className="space-y-4"><Skeleton className="h-48" /><Skeleton className="h-96" /></div>;

  if (run.isError) {
    body = <ErrorState message={`Agent run not found: ${runId}`} />;
  } else if (run.data) {
    const detail = run.data;
    body = (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Link href="/agents">
            <div className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-muted/50 transition-colors">
              <ArrowLeft size={16}/>
            </div>
          </Link>
          <div>
            <h2 className="font-mono text-xl font-bold tracking-tight">{detail.run_id}</h2>
            <p className="text-xs text-muted-foreground mt-0.5">{formatTime(detail.created_at)}</p>
          </div>
          <div className="ml-auto">
            <Badge tone={statusTone(detail.status)} className="px-3 py-1 text-xs">{detail.status}</Badge>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="bg-background/50">
            <CardContent className="p-4 flex flex-col justify-center">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1.5">Agent Identity</p>
              <div className="flex items-center gap-2"><Cpu size={14} className="text-accent"/> <span className="font-medium text-sm capitalize">{detail.agent_type}</span></div>
            </CardContent>
          </Card>
          <Card className="bg-background/50">
            <CardContent className="p-4 flex flex-col justify-center">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1.5">Invocation</p>
              <span className="font-mono text-sm capitalize">{detail.trigger}</span>
            </CardContent>
          </Card>
          <Card className="bg-background/50">
            <CardContent className="p-4 flex flex-col justify-center">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1.5">Tool Operations</p>
              <span className="font-mono text-lg font-bold">{detail.tool_calls.length}</span>
            </CardContent>
          </Card>
          <Card className="bg-background/50">
            <CardContent className="p-4 flex flex-col justify-center">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1.5">Approval State</p>
              <div className="mt-auto"><Badge tone={statusTone(detail.approval_status)}>{detail.approval_status}</Badge></div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader className="flex-row items-center justify-between border-b border-border/50 bg-muted/10 pb-3">
                <CardTitle className="flex items-center gap-2 text-base"><Terminal size={16} className="text-accent" /> Agent Workflow Execution</CardTitle>
                <div className="flex items-center bg-background/50 border border-border/50 p-1 rounded-xl text-xs">
                  <button
                    onClick={() => setViewMode("dag")}
                    className={`px-3 py-1 rounded-lg font-medium transition-all ${viewMode === "dag" ? "bg-accent text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                  >
                    Interactive DAG
                  </button>
                  <button
                    onClick={() => setViewMode("list")}
                    className={`px-3 py-1 rounded-lg font-medium transition-all ${viewMode === "list" ? "bg-accent text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                  >
                    Step List
                  </button>
                </div>
              </CardHeader>
              <CardContent className="p-4">
                {viewMode === "dag" ? (
                  <AgentRunDAG toolCalls={detail.tool_calls} trigger={detail.trigger} />
                ) : detail.tool_calls.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground text-sm">No tool executions recorded.</div>
                ) : (
                  <div className="divide-y divide-border/50 max-h-[500px] overflow-y-auto">
                    {detail.tool_calls.map((tc, i) => (
                      <div key={i} className="p-4 hover:bg-muted/10 transition-colors">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-muted text-[10px] font-bold text-muted-foreground">{i + 1}</span>
                            <span className="font-mono text-xs font-bold text-accent">{tc.tool}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-[11px] font-mono text-muted-foreground bg-background px-1.5 rounded border border-border/50">{formatMs(tc.duration_ms)}</span>
                            {tc.status === "success" ? <CheckCircle2 size={14} className="text-emerald-500" /> : <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />}
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                          <div className="bg-background/50 border border-border/40 rounded-lg p-2.5">
                            <p className="text-[9px] uppercase font-bold text-muted-foreground mb-1.5 ml-1">Input Arguments</p>
                            <JsonViewer data={tc.input} />
                          </div>
                          <div className="bg-background/50 border border-border/40 rounded-lg p-2.5">
                            <p className="text-[9px] uppercase font-bold text-muted-foreground mb-1.5 ml-1">Returned Observation</p>
                            <JsonViewer data={tc.output} />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="border-b border-border/50 bg-muted/10">
                <CardTitle className="flex items-center gap-2 text-base"><Sparkles size={16} className="text-amber-500" /> Final Outcome</CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                {detail.outcome ? (
                  typeof detail.outcome === "string" ? (
                    <p className="text-sm font-mono whitespace-pre-wrap">{detail.outcome}</p>
                  ) : (
                    <JsonViewer data={detail.outcome} />
                  )
                ) : (
                  <div className="text-center py-6 text-muted-foreground">
                    <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-accent mb-2"></div>
                    <p className="text-xs">Awaiting final outcome...</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader className="border-b border-border/50 bg-muted/10 pb-3">
                <CardTitle className="text-sm">Agent Plan</CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <ol className="relative border-l border-border/50 ml-2 space-y-4">
                  {Array.isArray(detail.plan)
                    ? detail.plan.map((step, i) => (
                        <li key={i} className="pl-4">
                          <div className="absolute w-2 h-2 bg-muted-foreground rounded-full -left-[4.5px] top-1.5 border border-background"></div>
                          <p className="text-xs font-medium leading-relaxed">
                            {typeof step === "string" ? step : String((step as Record<string, unknown>).name ?? JSON.stringify(step))}
                          </p>
                        </li>
                      ))
                    : <li className="text-xs pl-2">{String(detail.plan)}</li>}
                </ol>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="border-b border-border/50 bg-muted/10 pb-3">
                <CardTitle className="text-sm flex items-center gap-2"><FileCode2 size={14} className="text-accent" /> Proposed Action</CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                {detail.recommendation ? (
                  <JsonViewer data={detail.recommendation} />
                ) : (
                  <p className="text-xs text-muted-foreground italic text-center py-4">No recommendation proposed during this run.</p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  return <PageShell>{body}</PageShell>;
}
