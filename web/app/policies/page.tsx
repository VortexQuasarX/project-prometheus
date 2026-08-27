"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { PageShell } from "@/components/page-shell";
import { Button, Card, CardContent, CardHeader, CardTitle, CardDescription, ErrorState, Input, Label, Select, Skeleton, statusTone, Badge } from "@/components/ui";
import { getAudit, getPolicies, putPolicies } from "@/lib/api";
import type { KillSwitchMode, Policy } from "@/lib/types";

const BOOL_FIELDS: Array<{ key: keyof Policy; label: string }> = [
  { key: "require_cache_check", label: "Require cache check" },
  { key: "require_rag", label: "Require RAG grounding" },
  { key: "require_evaluation", label: "Require evaluation" },
  { key: "require_human_approval", label: "Require human approval" },
  { key: "pii_masking_enabled", label: "PII masking" },
  { key: "prompt_injection_detection_enabled", label: "Prompt-injection detection" },
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
    mutationFn: () => putPolicies(draft as Policy, reason),
    onSuccess: () => {
      toast.success("Policy saved — change is audited");
      setDraft(null);
      void queryClient.invalidateQueries({ queryKey: ["policies"] });
      void queryClient.invalidateQueries({ queryKey: ["audit"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const lastPolicyChange = (audit.data?.items ?? []).find((e) => e.action === "policy.updated");
  const dirty = policies.data?.policy && draft ? JSON.stringify(draft) !== JSON.stringify(policies.data.policy) : false;

  return (
    <PageShell>
      {policies.isLoading || draft === null ? (
        <Skeleton className="h-64" />
      ) : policies.isError ? (
        <ErrorState message={(policies.error as Error).message} />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Policy v{policies.data?.policy_version}</CardTitle>
              <CardDescription>
                {dirty ? "Unsaved changes" : "In sync"} · {lastPolicyChange ? `last change by ${lastPolicyChange.actor}` : "no changes yet"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                {NUM_FIELDS.map((f) => (
                  <div key={String(f.key)}>
                    <Label className="text-xs">{f.label}</Label>
                    <Input
                      type="number"
                      step={f.step}
                      value={String(draft[f.key] ?? "")}
                      onChange={(e) => setDraft({ ...draft, [f.key]: Number(e.target.value) })}
                    />
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-2">
                {BOOL_FIELDS.map((f) => (
                  <label key={String(f.key)} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(draft[f.key])}
                      onChange={(e) => setDraft({ ...draft, [f.key]: e.target.checked })}
                    />
                    {f.label}
                  </label>
                ))}
              </div>
              <div>
                <Label className="text-xs">Kill switch mode</Label>
                <Select
                  value={String(draft.kill_switch_mode)}
                  onChange={(e) => setDraft({ ...draft, kill_switch_mode: e.target.value as KillSwitchMode })}
                >
                  {["off", "cache_only", "cheap_only", "block_all"].map((m) => <option key={m} value={m}>{m}</option>)}
                </Select>
              </div>
              <div>
                <Label className="text-xs">Reason (audited)</Label>
                <Input value={reason} onChange={(e) => setReason(e.target.value)} />
              </div>
              <div className="flex items-center gap-2">
                <Button disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
                  {save.isPending ? "Saving..." : "Save policy"}
                </Button>
                {dirty ? <Button variant="outline" onClick={() => setDraft({ ...policies.data!.policy })}>Discard</Button> : null}
                <Badge tone={statusTone(String(draft.kill_switch_mode))}>{String(draft.kill_switch_mode)}</Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Audit note</CardTitle>
              <CardDescription>Latest policy.updated events (append-only)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              {(audit.data?.items ?? [])
                .filter((e) => e.action === "policy.updated")
                .slice(0, 8)
                .map((e) => (
                  <div key={e.event_id} className="rounded-lg border border-border p-2">
                    <p className="font-medium">{e.actor} · v{String(e.metadata.policy_version ?? "?")}</p>
                    <p className="text-muted-foreground">{String(e.metadata.reason ?? "")}</p>
                  </div>
                ))}
              {!lastPolicyChange ? <p className="text-muted-foreground">No policy changes yet.</p> : null}
            </CardContent>
          </Card>
        </div>
      )}
    </PageShell>
  );
}
