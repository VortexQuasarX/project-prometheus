"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Shield, Save, FileClock, SlidersHorizontal, ToggleRight, XCircle } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Button, Card, CardContent, CardHeader, CardTitle, CardDescription, ErrorState, Input, Label, Select, Skeleton, statusTone, Badge } from "@/components/ui";
import { getAudit, getPolicies, putPolicies } from "@/lib/api";
import type { KillSwitchMode, Policy } from "@/lib/types";
import { formatTime } from "@/lib/utils";

const BOOL_FIELDS: Array<{ key: keyof Policy; label: string; desc: string }> = [
  { key: "require_cache_check", label: "Semantic Caching", desc: "Cosine similarity vector check before LLM routing" },
  { key: "require_rag", label: "RAG Grounding", desc: "Inject enterprise context from pgvector" },
  { key: "require_evaluation", label: "LLM-as-a-Judge", desc: "Score responses for safety and relevance inline" },
  { key: "require_human_approval", label: "HITL Approvals", desc: "Require human sign-off for Agent policy changes" },
  { key: "pii_masking_enabled", label: "PII Masking", desc: "Regex scrubbing of SSN, CC, emails, phones" },
  { key: "prompt_injection_detection_enabled", label: "Injection Detection", desc: "Heuristic blocking of system prompt overrides" },
];

const NUM_FIELDS: Array<{ key: keyof Policy; label: string; step: string }> = [
  { key: "daily_budget_usd", label: "Daily budget (USD)", step: "0.1" },
  { key: "request_budget_usd", label: "Request budget (USD)", step: "0.01" },
  { key: "max_input_tokens", label: "Max input tokens", step: "50" },
  { key: "max_output_tokens", label: "Max output tokens", step: "50" },
  { key: "expensive_model_limit_per_day", label: "Expensive model calls / day", step: "1" },
  { key: "rate_limit_per_minute", label: "Rate limit / minute", step: "1" },
];

export default function PoliciesPage() {
  const queryClient = useQueryClient();
  const policies = useQuery({ queryKey: ["policies"], queryFn: getPolicies, retry: 0 });
  const audit = useQuery({ queryKey: ["audit"], queryFn: () => getAudit(50), retry: 0 });
  const [draft, setDraft] = useState<Policy | null>(null);
  const [reason, setReason] = useState("policy update from UI");

  useEffect(() => {
    if (policies.data?.policy && draft === null) setDraft({ ...policies.data.policy });
  }, [policies.data, draft]);

  const save = useMutation({
    mutationFn: () => putPolicies(draft!, reason),
    onSuccess: (data) => {
      toast.success(`Policy updated to version ${data.policy_version}`);
      setDraft({ ...data.policy });
      void queryClient.invalidateQueries({ queryKey: ["policies"] });
      void queryClient.invalidateQueries({ queryKey: ["audit"] });
      void queryClient.invalidateQueries({ queryKey: ["budget"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const lastPolicyChange = (audit.data?.items ?? []).find((e) => e.action === "policy.updated");
  const dirty = Boolean(
    draft &&
    policies.data?.policy &&
    JSON.stringify(draft) !== JSON.stringify(policies.data.policy)
  );

  return (
    <PageShell>
      {policies.isLoading || draft === null ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6"><Skeleton className="h-[600px] lg:col-span-2" /><Skeleton className="h-[600px]" /></div>
      ) : policies.isError ? (
        <ErrorState message={(policies.error as Error).message} />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 items-start">
          
          <Card className="lg:col-span-2">
            <CardHeader className="border-b border-border/50 bg-muted/10">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2"><Shield className="text-accent" size={20} /> Active Policy <Badge tone="blue">v{policies.data?.policy_version}</Badge></CardTitle>
                  <CardDescription className="mt-1">
                    {dirty ? <span className="text-amber-500 font-medium">● Unsaved changes</span> : <span className="text-emerald-500 font-medium">● In sync with cloud</span>}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {dirty && <Button variant="ghost" size="sm" onClick={() => setDraft({ ...policies.data!.policy })}>Discard</Button>}
                  <Button disabled={!dirty || save.isPending} onClick={() => save.mutate()} className="gap-2 shadow-lg">
                    <Save size={16} /> {save.isPending ? "Committing..." : "Commit Policy"}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-8 pt-6">
              
              {/* Toggles */}
              <div>
                <h4 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider mb-4"><ToggleRight size={16} /> Pipeline Features</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {BOOL_FIELDS.map((f) => (
                    <label key={String(f.key)} className="flex items-start gap-3 p-3 rounded-xl border border-border/40 hover:bg-muted/20 cursor-pointer transition-colors group">
                      <div className="relative flex items-center justify-center mt-0.5">
                        <input
                          type="checkbox"
                          className="peer sr-only"
                          checked={Boolean(draft[f.key])}
                          onChange={(e) => setDraft({ ...draft, [f.key]: e.target.checked })}
                        />
                        <div className="w-5 h-5 rounded bg-muted border border-border/80 peer-checked:bg-accent peer-checked:border-accent transition-colors flex items-center justify-center">
                          <svg className="w-3.5 h-3.5 text-white opacity-0 peer-checked:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-semibold group-hover:text-accent transition-colors">{f.label}</p>
                        <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">{f.desc}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Thresholds */}
              <div>
                <h4 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider mb-4"><SlidersHorizontal size={16} /> Thresholds & Limits</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {NUM_FIELDS.map((f) => (
                    <div key={String(f.key)} className="space-y-1.5">
                      <Label>{f.label}</Label>
                      <Input
                        type="number"
                        step={f.step}
                        value={String(draft[f.key] ?? "")}
                        onChange={(e) => setDraft({ ...draft, [f.key]: Number(e.target.value) })}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Kill Switch & Commit */}
              <div className="pt-6 border-t border-border/50 bg-muted/5 -mx-5 px-5 pb-2 rounded-b-xl">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <Label className="mb-1.5 block">Kill Switch Mode</Label>
                    <Select
                      value={String(draft.kill_switch_mode)}
                      className={draft.kill_switch_mode === "block_all" ? "border-red-500 text-red-500 focus:ring-red-500" : ""}
                      onChange={(e) => setDraft({ ...draft, kill_switch_mode: e.target.value as KillSwitchMode })}
                    >
                      {["off", "cache_only", "cheap_only", "block_all"].map((m) => <option key={m} value={m}>{m.replace('_', ' ').toUpperCase()}</option>)}
                    </Select>
                  </div>
                  <div>
                    <Label className="mb-1.5 block">Commit Reason (Audited)</Label>
                    <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g., Incident response, budget hike" />
                  </div>
                </div>
              </div>

            </CardContent>
          </Card>

          <Card className="h-full flex flex-col">
            <CardHeader className="border-b border-border/50 bg-muted/10">
              <CardTitle className="flex items-center gap-2"><FileClock size={18} /> Revision History</CardTitle>
              <CardDescription>Immutable trace of policy updates</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 p-0">
              <div className="divide-y divide-border/50">
                {(audit.data?.items ?? [])
                  .filter((e) => e.action === "policy.updated")
                  .slice(0, 10)
                  .map((e) => (
                    <div key={e.event_id} className="p-4 hover:bg-muted/20 transition-colors">
                      <div className="flex items-center justify-between mb-1">
                        <Badge tone="gray" className="font-mono bg-background">v{String(e.metadata.policy_version ?? "?")}</Badge>
                        <span className="text-[10px] text-muted-foreground">{formatTime(e.created_at)}</span>
                      </div>
                      <p className="text-sm font-medium">{e.actor}</p>
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">&quot;{String(e.metadata.reason ?? "No reason provided")}&quot;</p>
                    </div>
                  ))}
                {!lastPolicyChange ? <div className="p-8 text-center text-muted-foreground text-sm">No revisions recorded yet.</div> : null}
              </div>
            </CardContent>
          </Card>

        </div>
      )}
    </PageShell>
  );
}
