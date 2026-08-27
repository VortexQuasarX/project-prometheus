"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, ErrorState, Skeleton, Table, Td, Th, statusTone } from "@/components/ui";
import { approveAction, getPendingActions, rejectAction } from "@/lib/api";
import { formatUsd } from "@/lib/utils";

export default function ApprovalsPage() {
  const queryClient = useQueryClient();
  const pending = useQuery({ queryKey: ["pending-actions"], queryFn: getPendingActions, refetchInterval: 15_000, retry: 0 });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["pending-actions"] });
    void queryClient.invalidateQueries({ queryKey: ["agent-runs"] });
    void queryClient.invalidateQueries({ queryKey: ["budget"] });
    void queryClient.invalidateQueries({ queryKey: ["audit"] });
  };

  const approve = useMutation({
    mutationFn: (actionId: string) => approveAction(actionId, "approved from UI"),
    onSuccess: () => {
      toast.success("Action approved and policy applied");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const reject = useMutation({
    mutationFn: (actionId: string) => rejectAction(actionId, "rejected from UI"),
    onSuccess: () => {
      toast.success("Action rejected");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <PageShell>
      <Card>
        <CardHeader>
          <CardTitle>Pending approvals</CardTitle>
          <CardDescription>Human-in-the-loop gate for FinOps policy changes</CardDescription>
        </CardHeader>
        <CardContent>
          {pending.isLoading ? (
            <Skeleton className="h-40" />
          ) : pending.isError ? (
            <ErrorState message={(pending.error as Error).message} />
          ) : (pending.data?.items ?? []).length === 0 ? (
            <EmptyState title="Nothing waiting for approval" hint="Run the FinOps agent to generate actions." />
          ) : (
            <Table>
              <thead>
                <tr><Th>Action</Th><Th className="text-right">Expected saving</Th><Th>Risk</Th><Th>Latency impact</Th><Th className="text-right">Decision</Th></tr>
              </thead>
              <tbody>
                {(pending.data?.items ?? []).map((a) => (
                  <tr key={a.action_id} className="border-t border-border">
                    <Td>
                      <p className="text-sm font-medium">{a.title}</p>
                      <p className="font-mono text-xs text-muted-foreground">{a.action_id}</p>
                    </Td>
                    <Td className="tabular text-right">{formatUsd(a.expected_monthly_saving_usd, 2)}/mo</Td>
                    <Td><Badge tone={statusTone(a.risk_level === "low" ? "normal" : "critical")}>{a.risk_level}</Badge></Td>
                    <Td className="text-xs">{a.latency_impact}</Td>
                    <Td>
                      <div className="flex justify-end gap-2">
                        <Button size="sm" disabled={approve.isPending} onClick={() => approve.mutate(a.action_id)}>Approve</Button>
                        <Button size="sm" variant="destructive" disabled={reject.isPending} onClick={() => reject.mutate(a.action_id)}>Reject</Button>
                      </div>
                    </Td>
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
