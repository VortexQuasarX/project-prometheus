"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { Activity, Clock, Cpu, ArrowLeft, Terminal, Shield, Network } from "lucide-react";
import Link from "next/link";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, ErrorState, JsonViewer, Skeleton, statusTone } from "@/components/ui";
import { getTrace } from "@/lib/api";
import { formatMs, formatTime, formatUsd } from "@/lib/utils";
import { TraceGraph } from "@/components/TraceGraph";

// Map stage names to icons
const getStageIcon = (name: string) => {
  const lower = name.toLowerCase();
  if (lower.includes('guardrail')) return <Shield size={14} className="text-amber-500" />;
  if (lower.includes('cache')) return <Terminal size={14} className="text-blue-500" />;
  if (lower.includes('router') || lower.includes('route')) return <Network size={14} className="text-purple-500" />;
  if (lower.includes('llm') || lower.includes('generate')) return <Cpu size={14} className="text-emerald-500" />;
  return <Activity size={14} className="text-muted-foreground" />;
};

export default function TraceDetailPage() {
  const params = useParams<{ request_id: string }>();
  const requestId = params.request_id;
  const trace = useQuery({ queryKey: ["trace", requestId], queryFn: () => getTrace(requestId as string), retry: 0 });

  let body = <div className="space-y-4"><Skeleton className="h-48" /><Skeleton className="h-96" /></div>;
  
  if (trace.isError) {
    body = <ErrorState message={`Trace not found: ${requestId}`} />;
  } else if (trace.data) {
    const detail = trace.data;
    body = (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link href="/traces">
              <Button variant="ghost" size="icon" className="rounded-full h-8 w-8"><ArrowLeft size={16}/></Button>
            </Link>
            <div>
              <h2 className="font-mono text-xl font-bold tracking-tight">{detail.request_id}</h2>
              <p className="text-xs text-muted-foreground mt-0.5">{formatTime(detail.created_at)}</p>
            </div>
          </div>
          <Link href={`/playground?trace_id=${detail.request_id}`}>
            <Button variant="outline" className="gap-2 bg-accent/10 border-accent/30 text-accent hover:bg-accent/20">
              <Terminal size={16} /> Fork Trace to Playground
            </Button>
          </Link>
        </div>

        {/* Hero Metadata */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="bg-background/50">
            <CardContent className="p-4 flex flex-col justify-center">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Status</p>
              <div className="mt-auto"><Badge tone={statusTone(detail.status)}>{detail.status}</Badge></div>
            </CardContent>
          </Card>
          <Card className="bg-background/50">
            <CardContent className="p-4 flex flex-col justify-center">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Decision</p>
              <div className="mt-auto"><Badge tone={statusTone(detail.summary.router_decision as string)}>{String(detail.summary.router_decision ?? "—")}</Badge></div>
            </CardContent>
          </Card>
          <Card className="bg-background/50">
            <CardContent className="p-4 flex flex-col justify-center">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Model</p>
              <p className="font-mono text-sm truncate" title={String(detail.summary.model ?? "")}>{String(detail.summary.model ?? "—")}</p>
            </CardContent>
          </Card>
          <Card className="bg-background/50">
            <CardContent className="p-4 flex flex-col justify-center">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Cost</p>
              <p className="font-mono text-lg font-semibold text-emerald-500">{formatUsd(Number(detail.summary.cost_usd ?? 0), 5)}</p>
            </CardContent>
          </Card>
        </div>

        {/* Execution Timeline */}
        <Card>
          <CardHeader className="border-b border-border/50 bg-muted/10">
            <CardTitle className="flex items-center gap-2"><Clock size={18} className="text-accent" /> Execution Timeline</CardTitle>
            <CardDescription>Microsecond-level tracing through the 12-stage pipeline</CardDescription>
          </CardHeader>
          <CardContent className="pt-6 pl-2">
            <TraceGraph timeline={detail.timeline} />
          </CardContent>
        </Card>
      </div>
    );
  }

  return <PageShell>{body}</PageShell>;
}
