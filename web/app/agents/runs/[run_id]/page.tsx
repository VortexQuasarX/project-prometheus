"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { PageShell } from "@/components/page-shell";
import { Badge, Card, CardContent, CardHeader, CardTitle, ErrorState, JsonViewer, Skeleton, Table, Td, Th, statusTone } from "@/components/ui";
import { getAgentRun } from "@/lib/api";
import { formatMs, formatTime } from "@/lib/utils";

export default function AgentRunDetailPage() {
  const params = useParams<{ run_id: string }>();
  const runId = params.run_id;
  const run = useQuery({ queryKey: ["agent-run", runId], queryFn: () => getAgentRun(runId), retry: 0 });

  let body = <Skeleton className="h-64" />;
  if (run.isError) {
    body = <ErrorState message={`Agent run not found: ${runId}`} />;
  } else if (run.data) {
    const detail = run.data;
    body = (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CardTitle className="font-mono">{detail.run_id}</CardTitle>
              <Badge tone={statusTone(detail.status)}>{detail.status}</Badge>
              <Badge tone="gray">{detail.agent_type}</Badge>
              <Badge tone="gray">trigger: {detail.trigger}</Badge>
              <Badge tone={statusTone(detail.approval_status)}>approval: {detail.approval_status}</Badge>
            </div>
          </CardHeader>
        </Card>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Plan</CardTitle></CardHeader>
            <CardContent className="space-y-1 text-sm">
              {Array.isArray(detail.plan)
                ? detail.plan.map((step, i) => (
                    <p key={i} className="text-xs">
                      · {typeof step === "string" ? step : String((step as Record<string, unknown>).name ?? JSON.stringify(step))}
                    </p>
                  ))
                : <p className="text-xs">{String(detail.plan)}</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Recommendation</CardTitle></CardHeader>
            <CardContent>
              {detail.recommendation ? <JsonViewer data={detail.recommendation} /> : <p className="text-xs text-muted-foreground">No recommendation recorded.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Tool calls</CardTitle></CardHeader>
            <CardContent>
              {detail.tool_calls.length === 0 ? (
                <p className="text-xs text-muted-foreground">No tool calls recorded.</p>
              ) : (
                <Table>
                  <thead><tr><Th>Tool</Th><Th>Status</Th><Th className="text-right">Duration</Th></tr></thead>
                  <tbody>
                    {detail.tool_calls.map((tc, i) => (
                      <tr key={i} className="border-t border-border">
                        <Td className="font-mono text-xs">{tc.tool}</Td>
                        <Td><Badge tone={statusTone(tc.status === "success" ? "success" : "failed")}>{tc.status}</Badge></Td>
                        <Td className="tabular text-right text-xs">{formatMs(tc.duration_ms)}</Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Outcome</CardTitle></CardHeader>
            <CardContent>
              {detail.outcome ? <JsonViewer data={detail.outcome} /> : <p className="text-xs text-muted-foreground">Pending outcome.</p>}
              <p className="mt-2 text-xs text-muted-foreground">Updated {formatTime(detail.updated_at)}</p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return <PageShell>{body}</PageShell>;
}
