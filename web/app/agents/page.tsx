"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, ErrorState, Skeleton, Table, Td, Th, statusTone } from "@/components/ui";
import { getAgentRuns, runAgent } from "@/lib/api";
import { formatTime, formatUsd } from "@/lib/utils";

export default function AgentsPage() {
  const runs = useQuery({ queryKey: ["agent-runs"], queryFn: () => getAgentRuns(), refetchInterval: 15_000, retry: 0 });
  const trigger = useMutation({
    mutationFn: () => runAgent({ agent_type: "finops", trigger: "manual" }),
    onSuccess: () => {
      toast.success("FinOps agent run created");
      void runs.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <PageShell>
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Agent runs</CardTitle>
            <CardDescription>FinOps optimizer, reliability monitor and friends</CardDescription>
          </div>
          <Button size="sm" disabled={trigger.isPending} onClick={() => trigger.mutate()}>
            {trigger.isPending ? "Running..." : "Run FinOps Agent"}
          </Button>
        </CardHeader>
        <CardContent>
          {runs.isLoading ? (
            <Skeleton className="h-40" />
          ) : runs.isError ? (
            <ErrorState message={(runs.error as Error).message} />
          ) : (runs.data?.items ?? []).length === 0 ? (
            <EmptyState title="No agent runs yet" hint="Trigger the FinOps agent above." />
          ) : (
            <Table>
              <thead>
                <tr><Th>Run</Th><Th>Type</Th><Th>Trigger</Th><Th>Status</Th><Th>Recommendation</Th><Th className="text-right">Expected saving</Th><Th>Created</Th></tr>
              </thead>
              <tbody>
                {(runs.data?.items ?? []).map((r) => (
                  <tr key={r.run_id} className="border-t border-border hover:bg-muted/40">
                    <Td><Link className="font-mono text-xs text-accent hover:underline" href={`/agents/runs/${r.run_id}`}>{r.run_id}</Link></Td>
                    <Td className="text-xs">{r.agent_type}</Td>
                    <Td className="text-xs">{r.trigger}</Td>
                    <Td><Badge tone={statusTone(r.status)}>{r.status}</Badge></Td>
                    <Td className="max-w-64 truncate text-xs">{typeof r.recommendation === "string" ? r.recommendation : String((r.recommendation as Record<string, unknown> | null)?.title ?? "—")}</Td>
                    <Td className="tabular text-right">{formatUsd(r.expected_saving_usd ?? 0, 2)}</Td>
                    <Td className="text-xs text-muted-foreground">{formatTime(r.created_at)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </CardContent>
      </Card>
    </PageShell>
  );
}
