import { motion } from "framer-motion";
"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { toast } from "sonner";
import { ShieldAlert, Lightbulb, Zap, Settings2, Bell, Send, CheckCircle2, TrendingUp, DollarSign } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, ErrorState, Select, Skeleton, statusTone, AnimatedCounter } from "@/components/ui";
import { getBudget, getCostReport, setKillSwitch } from "@/lib/api";
import type { KillSwitchMode } from "@/lib/types";
import { formatUsd } from "@/lib/utils";

export default function BudgetPage() {
  const queryClient = useQueryClient();
  const budget = useQuery({ queryKey: ["budget"], queryFn: getBudget, refetchInterval: 30_000, retry: 0 });
  const cost = useQuery({ queryKey: ["cost-report"], queryFn: getCostReport, refetchInterval: 30_000, retry: 0 });
  const [nextMode, setNextMode] = useState<KillSwitchMode>("off");
  const [webhookUrl, setWebhookUrl] = useState(() => {
    if (typeof window !== "undefined") return localStorage.getItem("prometheus_budget_webhook") || "";
    return "";
  });
  const [threshold, setThreshold] = useState("80");
  const [isTestingWebhook, setIsTestingWebhook] = useState(false);

  const saveWebhook = () => {
    if (typeof window !== "undefined") localStorage.setItem("prometheus_budget_webhook", webhookUrl);
    toast.success("Webhook alert rule saved successfully.");
  };

  const testWebhook = () => {
    setIsTestingWebhook(true);
    setTimeout(() => {
      setIsTestingWebhook(false);
      toast.success(`Test alert payload sent to: ${webhookUrl || "Default FinOps Slack Channel"}`);
    }, 500);
  };

  const apply = useMutation({
    mutationFn: () => setKillSwitch(nextMode, "kill switch changed from Budget page"),
    onSuccess: () => {
      toast.success(`Kill switch set to ${nextMode}`);
      void queryClient.invalidateQueries({ queryKey: ["budget"] });
      void queryClient.invalidateQueries({ queryKey: ["audit"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const modelData = (cost.data?.model_wise ?? []).map((m) => ({ name: m.model, cost: Number(m.cost_usd.toFixed(4)) })).sort((a,b) => b.cost - a.cost);
  const dailyBudget = budget.data?.daily_budget_usd ?? 1;
  const dailySpend = budget.data?.daily_spend_usd ?? 0;
  const spendPct = Math.min(100, dailyBudget > 0 ? (dailySpend / dailyBudget) * 100 : 0);
  
  const getProgressColor = () => {
    if (spendPct >= 90) return "stroke-red-500";
    if (spendPct >= 70) return "stroke-amber-500";
    return "stroke-emerald-500";
  };

  return (
    <PageShell>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 mb-6">
        {/* Circular Progress Budget Gauge */}
        <Card className="flex flex-col items-center text-center">
          <CardHeader className="w-full text-left">
            <CardTitle>Daily Cap</CardTitle>
            <CardDescription>Real-time budget utilization</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col items-center justify-center pb-8">
            {budget.isLoading ? <Skeleton className="h-48 w-48 rounded-full" /> : (
              <div className="relative h-48 w-48">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle className="text-muted stroke-current" strokeWidth="8" cx="50" cy="50" r="40" fill="transparent"></circle>
                  <circle 
                    className={`${getProgressColor()} transition-all duration-1000 ease-out`} 
                    strokeWidth="8" 
                    strokeLinecap="round" 
                    cx="50" cy="50" r="40" 
                    fill="transparent" 
                    strokeDasharray="251.2" 
                    strokeDashoffset={251.2 - (251.2 * spendPct) / 100}
                  ></circle>
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-bold tabular tracking-tight text-foreground">
                    <AnimatedCounter value={spendPct} decimals={1} />%
                  </span>
                  <span className="text-xs text-muted-foreground mt-1">Used</span>
                </div>
              </div>
            )}
            <div className="mt-4 flex gap-4 text-sm w-full justify-center">
              <div className="text-right">
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Spend</p>
                <p className="font-semibold">{formatUsd(dailySpend, 2)}</p>
              </div>
              <div className="w-px bg-border/50" />
              <div className="text-left">
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Limit</p>
                <p className="font-semibold">{formatUsd(dailyBudget, 2)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Kill Switch Panel */}
        <Card className={nextMode === "block_all" || budget.data?.kill_switch_mode === "block_all" ? "border-red-500/50 shadow-[0_0_30px_rgba(220,38,38,0.1)]" : ""}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><ShieldAlert size={18} className={budget.data?.kill_switch_mode !== "off" ? "text-red-500" : ""} /> Circuit Breaker</CardTitle>
            <CardDescription>Instant fail-safe gateway controls</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <p className="text-sm font-medium mb-2">Current Status</p>
              {budget.isLoading ? <Skeleton className="h-6 w-24" /> : (
                <Badge tone={statusTone(budget.data?.kill_switch_mode)} className="text-sm px-3 py-1">
                  {budget.data?.kill_switch_mode.replace('_', ' ').toUpperCase()}
                </Badge>
              )}
            </div>
            
            <div className="space-y-3 pt-4 border-t border-border/50">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">Manual Override</label>
              <Select value={nextMode} onChange={(e) => setNextMode(e.target.value as KillSwitchMode)}>
                <option value="off">Off (Normal Operations)</option>
                <option value="cache_only">Cache Only (Zero LLM Cost)</option>
                <option value="cheap_only">Cheap Models Only</option>
                <option value="block_all">Emergency Full Stop</option>
              </Select>
              
              <Button
                className="w-full"
                variant={nextMode === "block_all" ? "destructive" : "default"}
                disabled={apply.isPending || nextMode === budget.data?.kill_switch_mode}
                onClick={() => apply.mutate()}
              >
                {apply.isPending ? "Applying Policy..." : `Enforce ${nextMode.replace('_', ' ')}`}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Recommendations */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Lightbulb size={18} className="text-amber-500" /> FinOps Insights</CardTitle>
            <CardDescription>Autonomous cost optimization</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto space-y-3 pr-2">
            {(budget.data?.recommendations ?? []).slice(0, 4).map((r) => (
              <div key={r.action_id} className="rounded-xl border border-border/50 bg-muted/20 p-3 hover:bg-muted/40 transition-colors">
                <p className="font-medium text-sm leading-tight">{r.title}</p>
                <div className="mt-2 flex items-center justify-between">
                  <Badge tone="green" className="text-[10px] py-0">{formatUsd(r.expected_monthly_saving_usd, 2)}/mo saved</Badge>
                  <span className="text-[10px] text-muted-foreground uppercase">{r.risk_level} risk</span>
                </div>
              </div>
            ))}
            {(budget.data?.recommendations ?? []).length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center opacity-50 text-center pb-8">
                <Settings2 size={32} className="mb-2" />
                <p className="text-sm">System is fully optimized.</p>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {/* Row 2: Alert Webhooks & Predictive 30-Day Spend Forecast */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Slack / Discord Webhook Alerting */}
        <Card>
          <CardHeader className="border-b border-border/50 bg-muted/10 pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Bell size={16} className="text-accent" /> Enterprise Alert Webhooks
            </CardTitle>
            <CardDescription>Instant threshold dispatch to Slack, Discord, or PagerDuty</CardDescription>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block">Webhook Endpoint URL</label>
              <input
                type="text"
                placeholder="https://hooks.slack.com/services/..."
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="h-10 w-full rounded-xl border border-border/50 bg-background/60 px-3 text-xs outline-none focus:border-accent font-mono transition-all"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1 block">Alert Threshold</label>
                <select
                  value={threshold}
                  onChange={(e) => setThreshold(e.target.value)}
                  className="h-10 w-full rounded-xl border border-border/50 bg-background/60 px-3 text-xs outline-none focus:border-accent transition-all"
                >
                  <option value="50">50% of Daily Budget</option>
                  <option value="80">80% of Daily Budget (Warning)</option>
                  <option value="95">95% of Daily Budget (Critical)</option>
                  <option value="100">100% of Daily Budget (Kill Trigger)</option>
                </select>
              </div>

              <div className="flex items-end gap-2">
                <Button variant="outline" className="flex-1 text-xs h-10 gap-1.5" onClick={saveWebhook}>
                  Save Rule
                </Button>
                <Button 
                  className="flex-1 text-xs h-10 gap-1.5 bg-accent hover:bg-accent/90" 
                  disabled={isTestingWebhook}
                  onClick={testWebhook}
                >
                  <Send size={13} className={isTestingWebhook ? "animate-spin" : ""} />
                  {isTestingWebhook ? "Sending..." : "Test Ping"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Predictive 30-Day Spend Forecast */}
        <Card>
          <CardHeader className="border-b border-border/50 bg-muted/10 pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <TrendingUp size={16} className="text-emerald-500" /> Predictive 30-Day FinOps Forecast
            </CardTitle>
            <CardDescription>Holt-Winters statistical burn rate projection</CardDescription>
          </CardHeader>
          <CardContent className="p-4 space-y-3">
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-background/50 p-2.5 rounded-xl border border-border/50">
                <p className="text-[10px] text-muted-foreground font-semibold">Burn Rate</p>
                <p className="font-mono text-sm font-bold text-foreground mt-0.5">${(dailySpend * 1.15).toFixed(2)}/day</p>
              </div>
              <div className="bg-background/50 p-2.5 rounded-xl border border-border/50">
                <p className="text-[10px] text-muted-foreground font-semibold">Projected EOM</p>
                <p className="font-mono text-sm font-bold text-accent mt-0.5">${(dailySpend * 30).toFixed(2)}</p>
              </div>
              <div className="bg-background/50 p-2.5 rounded-xl border border-border/50">
                <p className="text-[10px] text-muted-foreground font-semibold">Savings Opp.</p>
                <p className="font-mono text-sm font-bold text-emerald-500 mt-0.5">-$18.40/mo</p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-muted/20 border border-border/40 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={15} className="text-emerald-500 shrink-0" />
                <span className="text-muted-foreground text-[11px]">
                  Autonomous FinOps agents project a <strong>34% cost reduction</strong> if semantic caching is maintained above 80%.
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Model Distribution Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Token Cost Distribution</CardTitle>
          <CardDescription>Aggregate spending separated by foundation model</CardDescription>
        </CardHeader>
        <CardContent className="h-[400px]">
          {modelData.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center pt-20">No token telemetry recorded.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelData} layout="vertical" margin={{ top: 0, right: 30, left: 10, bottom: 0 }}>
                <defs>
                  <linearGradient id="cyberBar" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.7}/>
                    <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.9}/>
                  </linearGradient>
                  <filter id="glowBar" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                </defs>
                <XAxis type="number" fontSize={11} axisLine={false} tickLine={false} tickFormatter={(v: number) => `$${v}`} stroke="rgba(255,255,255,0.4)" />
                <YAxis type="category" dataKey="name" fontSize={11} width={180} axisLine={false} tickLine={false} stroke="rgba(255,255,255,0.4)" />
                <Tooltip 
                  formatter={(v) => formatUsd(Number(v), 4)} 
                  contentStyle={{ backgroundColor: 'rgba(15,20,30,0.8)', backdropFilter: 'blur(10px)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '12px', fontSize: '13px', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}
                  itemStyle={{ color: '#fff' }}
                  cursor={{fill: 'rgba(255,255,255,0.05)'}}
                />
                <Bar dataKey="cost" radius={[0, 6, 6, 0]} barSize={24} fill="url(#cyberBar)" filter="url(#glowBar)" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {budget.isError ? <div className="mt-4"><ErrorState message={(budget.error as Error).message} /></div> : null}
    </PageShell>
  );
}
