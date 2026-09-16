"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ShieldCheck, Check, X, AlertTriangle, ChevronRight } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, ErrorState, Skeleton, statusTone } from "@/components/ui";
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
      <div className="max-w-4xl mx-auto">
        <div className="mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-border/50 pb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <ShieldCheck className="text-accent" size={24} /> Human-in-the-Loop
            </h1>
            <p className="text-sm text-muted-foreground mt-1">Review and approve autonomous FinOps policy changes.</p>
          </div>
          <Badge tone={(pending.data?.items ?? []).length > 0 ? "amber" : "gray"} className="w-fit text-sm px-3 py-1">
            {(pending.data?.items ?? []).length} Actions Pending
          </Badge>
        </div>

        {pending.isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : pending.isError ? (
          <ErrorState message={(pending.error as Error).message} />
        ) : (pending.data?.items ?? []).length === 0 ? (
          <EmptyState 
            title="Inbox Zero" 
            hint="The FinOps agent hasn't queued any actions requiring your approval." 
            icon={<Check size={48} className="text-emerald-500/50" />} 
          />
        ) : (
          <div className="space-y-4">
            {(pending.data?.items ?? []).map((a) => (
              <Card key={a.action_id} className="group hover:border-accent/30 transition-colors">
                <div className="flex flex-col sm:flex-row">
                  {/* Left content area */}
                  <div className="flex-1 p-5 border-b sm:border-b-0 sm:border-r border-border/50">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {a.risk_level === "critical" ? <AlertTriangle size={16} className="text-red-500" /> : <ShieldCheck size={16} className="text-emerald-500" />}
                        <h3 className="font-semibold text-base">{a.title}</h3>
                      </div>
                      <Badge tone={statusTone(a.risk_level === "low" ? "normal" : "critical")}>{a.risk_level}</Badge>
                    </div>
                    
                    <p className="text-[10px] font-mono text-muted-foreground bg-muted/30 px-2 py-0.5 rounded w-fit mb-4">
                      {a.action_id}
                    </p>
                    
                    <div className="grid grid-cols-2 gap-4 mt-4 bg-muted/10 rounded-lg p-3">
                      <div>
                        <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Projected Impact</p>
                        <p className="text-lg font-bold text-emerald-500 mt-0.5">{formatUsd(a.expected_monthly_saving_usd, 2)}<span className="text-xs text-muted-foreground font-normal"> /mo</span></p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Latency Trade-off</p>
                        <p className="text-sm font-medium mt-1.5">{a.latency_impact}</p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Right actions area */}
                  <div className="p-5 sm:w-48 bg-muted/5 flex flex-col justify-center gap-3">
                    <Button 
                      className="w-full justify-between shadow-sm bg-emerald-600 hover:bg-emerald-700 text-white" 
                      disabled={approve.isPending || reject.isPending} 
                      onClick={() => approve.mutate(a.action_id)}
                    >
                      Approve <Check size={16} />
                    </Button>
                    <Button 
                      variant="outline"
                      className="w-full justify-between hover:bg-red-500/10 hover:text-red-500 hover:border-red-500/30" 
                      disabled={approve.isPending || reject.isPending} 
                      onClick={() => reject.mutate(a.action_id)}
                    >
                      Reject <X size={16} />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </PageShell>
  );
}
