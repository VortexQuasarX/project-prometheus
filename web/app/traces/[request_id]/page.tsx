"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { PageShell } from "@/components/page-shell";
import { Badge, Card, CardContent, CardHeader, CardTitle, ErrorState, JsonViewer, Skeleton, statusTone } from "@/components/ui";
import { getTrace } from "@/lib/api";
import { formatMs, formatTime, formatUsd } from "@/lib/utils";

export default function TraceDetailPage() {
  const params = useParams<{ request_id: string }>();
  const requestId = params.request_id;
  const trace = useQuery({ queryKey: ["trace", requestId], queryFn: () => getTrace(requestId), retry: 0 });

  let body = <Skeleton className="h-64" />;
  if (trace.isError) {
    body = <ErrorState message={`Trace not found: ${requestId}`} />;
  } else if (trace.data) {
    const detail = trace.data;
    body = (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="font-mono">{detail.request_id}</CardTitle>
            <div className="flex flex-wrap gap-1.5 text-xs">
              <Badge tone={statusTone(detail.status)}>{detail.status}</Badge>
              <Badge tone="gray">{String(detail.summary.model ?? "—")}</Badge>
              <Badge tone={statusTone(detail.summary.router_decision as string)}>
                {String(detail.summary.router_decision ?? "—")}
              </Badge>
              <Badge tone="gray">cost {formatUsd(Number(detail.summary.cost_usd ?? 0))}</Badge>
            </div>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader><CardTitle>Timeline</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {detail.timeline.map((e, i) => (
              <div key={`${e.name}-${i}`} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="mt-1 h-2 w-2 rounded-full bg-accent" />
                  {i < detail.timeline.length - 1 ? <div className="h-full w-px bg-border" /> : null}
                </div>
                <div className="flex-1 pb-2">
                  <div className="flex items-center justify-between">
                    <p className="font-mono text-xs font-semibold">{e.name}</p>
                    <p className="tabular text-xs text-muted-foreground">
                      {formatMs(e.duration_ms)} · {formatTime(e.timestamp)}
                    </p>
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge tone={statusTone(e.status)}>{e.status}</Badge>
                  </div>
                  {e.metadata && Object.keys(e.metadata).length > 0 ? (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-xs text-muted-foreground">metadata</summary>
                      <JsonViewer data={e.metadata} />
                    </details>
                  ) : null}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  return <PageShell>{body}</PageShell>;
}
