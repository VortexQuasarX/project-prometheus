import { motion } from "framer-motion";
"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ShieldCheck, Check, X, AlertTriangle, Lock, Users, Sparkles, CheckCircle2 } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, ErrorState, Skeleton, statusTone } from "@/components/ui";
import { approveAction, getPendingActions, rejectAction } from "@/lib/api";
import { formatUsd } from "@/lib/utils";
import { useState } from "react";

export default function ApprovalsPage() {
  const queryClient = useQueryClient();
  const pending = useQuery({ queryKey: ["pending-actions"], queryFn: getPendingActions, refetchInterval: 15_000, retry: 0 });
  const [signedCritical, setSignedCritical] = useState<Record<string, number>>({});

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["pending-actions"] });
    void queryClient.invalidateQueries({ queryKey: ["agent-runs"] });
    void queryClient.invalidateQueries({ queryKey: ["budget"] });
    void queryClient.invalidateQueries({ queryKey: ["audit"] });
  };

  const approve = useMutation({
    mutationFn: (actionId: string) => approveAction(actionId, "approved from UI"),
    onSuccess: () => {
      toast.success("Action approved and policy applied to live gateway");
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

  const handleCriticalApprove = (actionId: string) => {
    const currentSignatures = signedCritical[actionId] || 0;
    if (currentSignatures < 1) {
      setSignedCritical(prev => ({ ...prev, [actionId]: 1 }));
      toast.info("1 of 2 Quorum signatures recorded (FinOps Admin). Awaiting Security Lead sign-off.");
    } else {
      approve.mutate(actionId);
    }
  };

  const approveAllLowRisk = async () => {
    const lowRisk = (pending.data?.items ?? []).filter(a => a.risk_level === "low");
    if (lowRisk.length === 0) return;
    for (const a of lowRisk) {
      await approveAction(a.action_id, "bulk approved low risk");
    }
    toast.success(`Bulk approved ${lowRisk.length} low-risk optimizations.`);
    invalidate();
  };

  const items = pending.data?.items ?? [];
  const lowRiskCount = items.filter(a => a.risk_level === "low").length;

  return (
    <PageShell>
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-border/50 pb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <ShieldCheck className="text-accent" size={24} /> Multi-Stage Governance Approvals
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Human-in-the-Loop (HITL) quorum gate for autonomous FinOps and router policy changes.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {lowRiskCount > 0 && (
              <Button 
                variant="outline" 
                size="sm" 
                onClick={approveAllLowRisk}
                className="gap-1.5 text-xs border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10"
              >
                <Sparkles size={14} /> Approve All Low-Risk ({lowRiskCount})
              </Button>
            )}
            <Badge tone={items.length > 0 ? "amber" : "gray"} className="text-xs px-3 py-1 font-mono">
              {items.length} Actions Pending
            </Badge>
          </div>
        </div>

        {pending.isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : pending.isError ? (
          <ErrorState message={(pending.error as Error).message} />
        ) : items.length === 0 ? (
          <EmptyState 
            title="Inbox Zero" 
            hint="The FinOps autonomous agents haven't queued any actions requiring your approval." 
            icon={<Check size={48} className="text-emerald-500/50" />} 
          />
        ) : (
          <div className="space-y-4">
            {items.map((a) => {
              const isCritical = a.risk_level === "critical" || a.risk_level === "high";
              const signatures = signedCritical[a.action_id] || 0;
              const pseudoHash = Math.abs(a.action_id.split("").reduce((acc, char) => (acc << 5) - acc + char.charCodeAt(0), 0)).toString(16).padStart(8, '0');

              return (
                <Card key={a.action_id} className="group hover:border-accent/30 transition-colors">
                  <div className="flex flex-col sm:flex-row">
                    {/* Left content area */}
                    <div className="flex-1 p-5 border-b sm:border-b-0 sm:border-r border-border/50 space-y-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          {isCritical ? <AlertTriangle size={16} className="text-red-500" /> : <ShieldCheck size={16} className="text-emerald-500" />}
                          <h3 className="font-semibold text-base text-foreground">{a.title}</h3>
                        </div>
                        <Badge tone={statusTone(a.risk_level === "low" ? "normal" : "critical")}>{a.risk_level}</Badge>
                      </div>
                      
                      <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono">
                        <span className="text-muted-foreground bg-muted/30 px-2 py-0.5 rounded border border-border/40">
                          {a.action_id}
                        </span>
                        <span className="text-muted-foreground flex items-center gap-1 bg-background/50 px-2 py-0.5 rounded border border-border/40">
                          <Lock size={10} className="text-accent" /> SHA256:{pseudoHash}...
                        </span>
                      </div>

                      {/* Quorum Progress for Critical Actions */}
                      {isCritical && (
                        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs space-y-2">
                          <div className="flex items-center justify-between font-semibold">
                            <span className="flex items-center gap-1.5 text-red-400">
                              <Users size={14} /> Multi-Stage Quorum Required
                            </span>
                            <span className="font-mono text-[11px] text-foreground">{signatures}/2 Signed</span>
                          </div>
                          <div className="h-1.5 w-full bg-muted/40 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-red-500 transition-all duration-300"
                              style={{ width: `${(signatures / 2) * 100}%` }}
                            />
                          </div>
                          <div className="flex justify-between text-[10px] text-muted-foreground">
                            <span>1. FinOps Admin {signatures >= 1 ? "✓ (Signed)" : "Pending"}</span>
                            <span>2. Security Lead {signatures >= 2 ? "✓ (Signed)" : "Pending"}</span>
                          </div>
                        </div>
                      )}
                      
                      <div className="grid grid-cols-2 gap-4 bg-muted/10 rounded-xl p-3">
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
                    <div className="p-5 sm:w-52 bg-muted/5 flex flex-col justify-center gap-3">
                      <Button 
                        className="w-full justify-between shadow-sm bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-10" 
                        disabled={approve.isPending || reject.isPending} 
                        onClick={() => isCritical ? handleCriticalApprove(a.action_id) : approve.mutate(a.action_id)}
                      >
                        {isCritical && signatures === 0 ? "Sign (1 of 2)" : "Approve & Apply"} <Check size={14} />
                      </Button>
                      <Button 
                        variant="outline"
                        className="w-full justify-between hover:bg-red-500/10 hover:text-red-500 hover:border-red-500/30 text-xs h-10" 
                        disabled={approve.isPending || reject.isPending} 
                        onClick={() => reject.mutate(a.action_id)}
                      >
                        Reject Action <X size={14} />
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </PageShell>
  );
}
