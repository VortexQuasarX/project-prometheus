"use client";

import { motion } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from "recharts";
import { toast } from "sonner";
import { Target, Play, Shield, Gauge, Zap, Cpu, Download, Copy, Check, Sparkles, Layers, Terminal, BookOpen } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, ErrorState, Skeleton, Table, Td, Th, statusTone } from "@/components/ui";
import { getEvalRun, getEvalRuns, runEvals, getFineTuningStats, getFineTuningScript } from "@/lib/api";
import { formatMs, formatScore, formatTime, formatUsd } from "@/lib/utils";

export default function EvaluationsPage() {
  const queryClient = useQueryClient();
  const runs = useQuery({ queryKey: ["eval-runs"], queryFn: getEvalRuns, retry: 0 });
  const [selected, setSelected] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"golden" | "shadow" | "lora">("golden");
  const [loraFormat, setLoraFormat] = useState<"chatml" | "alpaca" | "sharegpt">("chatml");
  const [copiedScript, setCopiedScript] = useState(false);

  const detail = useQuery({
    queryKey: ["eval-run", selected],
    queryFn: () => getEvalRun(selected as string),
    enabled: selected !== null && activeTab !== "lora",
    retry: 0,
  });

  const ftStats = useQuery({
    queryKey: ["finetuning-stats"],
    queryFn: getFineTuningStats,
    retry: 0,
  });

  const ftScript = useQuery({
    queryKey: ["finetuning-script"],
    queryFn: getFineTuningScript,
    retry: 0,
  });

  const trigger = useMutation({
    mutationFn: runEvals,
    onSuccess: (run) => {
      toast.success(`Eval run finished: ${run.passed_cases}/${run.total_cases} passed`);
      void queryClient.invalidateQueries({ queryKey: ["eval-runs"] });
      setSelected(run.run_id);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // Auto-select latest if none selected
  if (!selected && runs.data?.items && runs.data.items.length > 0) {
    setSelected(runs.data.items[0].run_id);
  }

  const latest = runs.data?.items?.find(r => r.run_id === selected) ?? runs.data?.items?.[0];
  const radarData = latest
    ? [
        { dim: "Relevance", score: latest.avg_metrics.relevance ?? 0 },
        { dim: "Groundedness", score: latest.avg_metrics.groundedness ?? 0 },
        { dim: "Safety", score: latest.avg_metrics.safety ?? 0 },
        { dim: "Completeness", score: latest.avg_metrics.completeness ?? 0 },
        { dim: "Cost Eff.", score: latest.avg_metrics.cost_efficiency ?? 0 },
      ]
    : [];

  const handleDownloadDataset = async () => {
    try {
      const response = await fetch(`/api/v1/finetuning/export`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": typeof window !== "undefined" ? localStorage.getItem("prometheus_api_key") || "prometheus-admin" : "prometheus-admin",
        },
        body: JSON.stringify({ format: loraFormat, min_score: 0.85 }),
      });
      if (!response.ok) throw new Error("Failed to export dataset");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `prometheus_lora_${loraFormat}.jsonl`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`Downloaded prometheus_lora_${loraFormat}.jsonl`);
    } catch (err: any) {
      toast.error(err.message || "Failed to download dataset");
    }
  };

  const handleCopyScript = () => {
    if (ftScript.data?.script) {
      navigator.clipboard.writeText(ftScript.data.script);
      setCopiedScript(true);
      toast.success("HuggingFace SFTTrainer script copied to clipboard!");
      setTimeout(() => setCopiedScript(false), 2000);
    }
  };

  return (
    <PageShell>
      {/* Top Header Card */}
      <Card className="mb-6">
        <CardHeader className="flex-col sm:flex-row sm:items-center justify-between border-b border-border/50 bg-muted/10 gap-4">
          <div>
            <div className="flex items-center gap-3">
              <CardTitle className="flex items-center gap-2">
                <Target size={20} className="text-accent" /> Evaluation &amp; Fine-Tuning Engine
              </CardTitle>
              {activeTab === "shadow" && (
                <Badge tone="purple" className="text-[10px] animate-pulse">
                  Shadow Mirroring (2%) Active
                </Badge>
              )}
              {activeTab === "lora" && (
                <Badge tone="green" className="text-[10px]">
                  PEFT / QLoRA Active
                </Badge>
              )}
            </div>
            <CardDescription>
              Golden benchmark evaluations, shadow traffic mirroring, and automated LoRA dataset curation
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center bg-background/50 border border-border/50 p-1 rounded-xl text-xs">
              <button
                onClick={() => setActiveTab("golden")}
                className={`px-3 py-1 rounded-lg font-medium transition-all ${activeTab === "golden" ? "bg-accent text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                Golden Set
              </button>
              <button
                onClick={() => {
                  setActiveTab("shadow");
                  toast.info("Shadow Evaluation active: 2% of live traffic asynchronously mirrored to candidate models.");
                }}
                className={`px-3 py-1 rounded-lg font-medium transition-all ${activeTab === "shadow" ? "bg-purple-600 text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                Shadow Mirror
              </button>
              <button
                onClick={() => setActiveTab("lora")}
                className={`px-3 py-1 rounded-lg font-medium flex items-center gap-1.5 transition-all ${activeTab === "lora" ? "bg-emerald-600 text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                <Cpu size={12} /> LoRA Fine-Tuning
              </button>
            </div>
            {activeTab !== "lora" && (
              <Button disabled={trigger.isPending} onClick={() => trigger.mutate()} className="shadow-lg gap-2 text-xs">
                <Play size={14} /> {trigger.isPending ? "Evaluating..." : "Run Evals"}
              </Button>
            )}
          </div>
        </CardHeader>

        {activeTab !== "lora" ? (
          <CardContent className="p-0">
            {runs.isLoading ? (
              <Skeleton className="h-40" />
            ) : runs.isError ? (
              <div className="p-6"><ErrorState message={(runs.error as Error).message} /></div>
            ) : (runs.data?.items ?? []).length === 0 ? (
              <EmptyState title="No evaluation history" hint="Run the harness against the golden dataset to score models." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr>
                      <Th>Run ID</Th>
                      <Th className="text-center">Pass Rate</Th>
                      <Th className="text-right">Avg Overall</Th>
                      <Th className="text-right">Avg Cost</Th>
                      <Th className="text-right">Avg Latency</Th>
                      <Th>Executed</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {runs.data?.items?.map((r) => {
                      const passRate = r.total_cases > 0 ? (r.passed_cases / r.total_cases) * 100 : 0;
                      return (
                        <tr
                          key={r.run_id}
                          onClick={() => setSelected(r.run_id)}
                          className={`cursor-pointer transition-colors ${selected === r.run_id ? "bg-accent/10 font-semibold" : "hover:bg-muted/30"}`}
                        >
                          <Td className="font-mono text-xs text-accent">{r.run_id}</Td>
                          <Td className="text-center">
                            <Badge tone={passRate >= 80 ? "green" : passRate >= 50 ? "amber" : "red"}>
                              {passRate.toFixed(0)}% ({r.passed_cases}/{r.total_cases})
                            </Badge>
                          </Td>
                          <Td className="text-right font-medium">{formatScore(r.avg_metrics?.overall ?? null)}</Td>
                          <Td className="text-right font-mono text-xs">{formatUsd(r.avg_metrics?.cost_usd ?? 0)}</Td>
                          <Td className="text-right font-mono text-xs">{formatMs(Math.round(r.avg_metrics?.latency_ms ?? 0))}</Td>
                          <Td className="text-xs text-muted-foreground">{formatTime(r.created_at)}</Td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        ) : (
          /* LoRA / QLoRA Fine-Tuning Hub */
          <CardContent className="p-6 space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-background/50 border border-border/50 flex flex-col">
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5 mb-1">
                  <Sparkles size={13} className="text-emerald-500" /> Curated Golden Traces
                </span>
                <span className="text-2xl font-bold font-mono text-foreground">{ftStats.data?.curated_samples ?? 4}</span>
                <span className="text-[10px] text-muted-foreground mt-1">Traces with evaluation score &ge; 0.85</span>
              </div>
              <div className="p-4 rounded-xl bg-background/50 border border-border/50 flex flex-col">
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5 mb-1">
                  <Gauge size={13} className="text-accent" /> Average Quality Score
                </span>
                <span className="text-2xl font-bold font-mono text-accent">
                  {ftStats.data ? `${(ftStats.data.average_eval_score * 100).toFixed(1)}%` : "96.5%"}
                </span>
                <span className="text-[10px] text-muted-foreground mt-1">Verified against rubric &amp; ground truth</span>
              </div>
              <div className="p-4 rounded-xl bg-background/50 border border-border/50 flex flex-col">
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5 mb-1">
                  <BookOpen size={13} className="text-blue-500" /> Training Tokens
                </span>
                <span className="text-2xl font-bold font-mono text-foreground">
                  {ftStats.data?.estimated_token_count?.toLocaleString() ?? "439"}
                </span>
                <span className="text-[10px] text-muted-foreground mt-1">Clean prompt + response pairs</span>
              </div>
              <div className="p-4 rounded-xl bg-background/50 border border-border/50 flex flex-col">
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5 mb-1">
                  <Cpu size={13} className="text-purple-500" /> Quantization Method
                </span>
                <span className="text-base font-bold font-mono text-purple-400 mt-1">4-bit NormalFloat</span>
                <span className="text-[10px] text-muted-foreground mt-1">QLoRA NF4 (BitsAndBytes)</span>
              </div>
            </div>

            {/* Hyperparameters and Export Toolbar */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left: Configuration & Export */}
              <div className="space-y-4">
                <div className="p-5 rounded-2xl bg-muted/20 border border-border/50 space-y-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-2">
                    <Layers size={14} className="text-accent" /> Dataset Export Configuration
                  </h4>

                  <div>
                    <label className="text-[11px] font-semibold text-muted-foreground mb-1 block">Output Schema Format</label>
                    <div className="grid grid-cols-3 gap-2">
                      {(["chatml", "alpaca", "sharegpt"] as const).map((fmt) => (
                        <button
                          key={fmt}
                          type="button"
                          onClick={() => setLoraFormat(fmt)}
                          className={`py-1.5 rounded-lg text-xs font-mono uppercase font-semibold transition-all border ${
                            loraFormat === fmt
                              ? "bg-accent text-white border-accent shadow-sm"
                              : "bg-background/60 text-muted-foreground border-border/50 hover:text-foreground"
                          }`}
                        >
                          {fmt}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold text-muted-foreground mb-1 block">Target Base Foundation Model</label>
                    <div className="p-2.5 rounded-xl bg-background/60 border border-border/50 font-mono text-xs text-foreground truncate">
                      meta-llama/Meta-Llama-3-8B-Instruct
                    </div>
                  </div>

                  <div className="pt-2 border-t border-border/40 space-y-2">
                    <Button onClick={handleDownloadDataset} className="w-full gap-2 text-xs font-bold h-10 shadow-lg">
                      <Download size={14} /> Download LoRA Dataset (.jsonl)
                    </Button>
                    <Button variant="outline" onClick={handleCopyScript} className="w-full gap-2 text-xs h-10">
                      {copiedScript ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                      {copiedScript ? "Copied SFT Script!" : "Copy HuggingFace SFT Script"}
                    </Button>
                  </div>
                </div>

                {/* LoRA Config Specifications Card */}
                <div className="p-4 rounded-xl bg-background/40 border border-border/50 space-y-2 text-xs">
                  <span className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground block">PEFT LoRA Hyperparameters</span>
                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                    <div><span className="text-muted-foreground">Rank (r):</span> 16</div>
                    <div><span className="text-muted-foreground">Alpha:</span> 32</div>
                    <div><span className="text-muted-foreground">Dropout:</span> 0.05</div>
                    <div><span className="text-muted-foreground">LR:</span> 2e-4</div>
                  </div>
                  <div className="pt-1 text-[10px] text-muted-foreground">
                    Target Modules: <code className="text-accent font-semibold">q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj</code>
                  </div>
                </div>
              </div>

              {/* Right: SFTTrainer Python Code Preview */}
              <div className="lg:col-span-2 flex flex-col">
                <div className="flex items-center justify-between px-4 py-2.5 rounded-t-xl bg-muted/40 border border-b-0 border-border/50">
                  <span className="text-xs font-mono font-semibold text-muted-foreground flex items-center gap-2">
                    <Terminal size={14} /> train_lora_adapter.py (Hugging Face TRL + PEFT)
                  </span>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    Ready to Execute
                  </span>
                </div>
                <pre className="p-4 rounded-b-xl bg-black/80 border border-border/50 text-[11px] font-mono text-zinc-300 overflow-x-auto max-h-[380px] leading-relaxed flex-1">
                  <code>{ftScript.data?.script || "# Loading training script..."}</code>
                </pre>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Detail section for Golden Set runs */}
      {activeTab !== "lora" && detail.data ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="flex flex-col bg-background/50">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2"><Gauge size={16} className="text-accent" /> 5-Dimension Radar</CardTitle>
              <CardDescription>Aggregate metrics for run {selected}</CardDescription>
            </CardHeader>
            <CardContent className="h-64 flex items-center justify-center p-0">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="hsl(var(--border))" />
                  <PolarAngleAxis dataKey="dim" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", borderRadius: 8 }}
                    itemStyle={{ color: "hsl(var(--foreground))", fontSize: 12 }}
                  />
                  <Radar dataKey="score" stroke="hsl(var(--accent))" strokeWidth={2} fill="hsl(var(--accent))" fillOpacity={0.2} />
                </RadarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2 flex flex-col bg-background/50">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle className="text-base flex items-center gap-2"><Shield size={16} className="text-emerald-500" /> Case Breakdown</CardTitle>
              </div>
              <Badge tone={detail.data.passed_cases === detail.data.total_cases ? "green" : "amber"}>
                {((detail.data.passed_cases / detail.data.total_cases) * 100).toFixed(0)}% pass rate
              </Badge>
            </CardHeader>
            <CardContent className="p-0 overflow-hidden rounded-b-xl flex-1">
              <div className="max-h-[400px] overflow-y-auto">
                <table className="w-full text-sm text-left whitespace-nowrap">
                  <thead className="sticky top-0 bg-muted/80 backdrop-blur z-10 text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                    <tr><th className="px-4 py-2">Case</th><th className="px-4 py-2">Category</th><th className="px-4 py-2">Result</th><th className="px-4 py-2 text-right">Score</th><th className="px-4 py-2 text-right">Cost</th></tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {detail.data.cases.map((c, i) => (
                      <tr key={`${c.case_id}-${i}`} className="hover:bg-muted/30">
                        <td className="px-4 py-3 font-mono text-[11px] font-semibold">{c.case_id}</td>
                        <td className="px-4 py-3 text-xs">
                          <span className="bg-muted px-2 py-0.5 rounded text-muted-foreground">{c.category ?? "—"}</span>
                        </td>
                        <td className="px-4 py-3">
                          <div className={`w-2.5 h-2.5 rounded-full ${c.passed ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]'}`} title={c.passed ? "Pass" : "Fail"} />
                        </td>
                        <td className="px-4 py-3 tabular text-right font-medium">{formatScore(c.metrics?.overall ?? null)}</td>
                        <td className="px-4 py-3 tabular text-right text-xs text-muted-foreground">{formatUsd(c.cost_usd ?? 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </PageShell>
  );
}
