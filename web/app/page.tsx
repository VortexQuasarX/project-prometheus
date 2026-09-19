"use client";
import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useTheme } from "next-themes";
import { motion } from "framer-motion";
import { Activity, Zap, CheckCircle2, ArrowRight, Wallet, Target, Clock, Bot, ShieldAlert } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, Progress, Badge, Skeleton, EmptyState, statusTone, Table, Th, Td, AnimatedCounter } from "@/components/ui";
import { formatMs, formatPercent, formatUsd } from "@/lib/utils";
import Link from "next/link";
import { getMetrics, getCostReport, getCacheStats, getBudget, getPendingActions, getAgentRuns } from "@/lib/api";

function MetricCard({ title, value, sub, icon, variants, label, className }: any) {
  return (
    <motion.div variants={variants} className={`glass-card p-5 flex flex-col justify-between h-full group gradient-border relative ${className}`}>
      <div className="pointer-events-none absolute -inset-px rounded-xl opacity-0 transition duration-300 group-hover:opacity-100 dark:hidden" style={{ background: "radial-gradient(600px circle at var(--mouse-x) var(--mouse-y), rgba(0,0,0,0.03), transparent 40%)" }} />
      <div className="pointer-events-none absolute -inset-px rounded-xl opacity-0 transition duration-300 group-hover:opacity-100 hidden dark:block" style={{ background: "radial-gradient(600px circle at var(--mouse-x) var(--mouse-y), rgba(255,255,255,0.06), transparent 40%)" }} />
      
      <div className="flex items-center justify-between mb-4 relative z-10">
        <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{label || title}</p>
        <div className="p-2 rounded-lg bg-primary/10 text-primary group-hover:scale-110 transition-transform">{icon}</div>
      </div>
      <div className="relative z-10">
        <h3 className="text-3xl font-extrabold tracking-tight text-foreground">{value}</h3>
        <p className="text-[10px] font-bold text-muted-foreground/80 mt-2 uppercase tracking-wide">{sub}</p>
      </div>
    </motion.div>
  );
}

export default function DashboardPage() {
  const { theme } = useTheme();
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: getMetrics, refetchInterval: 30000 });
  const cost = useQuery({ queryKey: ["cost-report"], queryFn: getCostReport, refetchInterval: 30000 });
  const cache = useQuery({ queryKey: ["cache-stats"], queryFn: getCacheStats, refetchInterval: 30000 });
  const budget = useQuery({ queryKey: ["budget"], queryFn: getBudget, refetchInterval: 30000 });
  const pending = useQuery({ queryKey: ["pending-actions"], queryFn: getPendingActions, refetchInterval: 30000 });
  const agentRuns = useQuery({ queryKey: ["agent-runs"], queryFn: () => getAgentRuns(), refetchInterval: 30000 });

  const activeAgentCount = Math.max(1, (agentRuns.data?.items ?? []).filter((r: any) => r.status === "running" || r.status === "pending" || r.status === "verified").length);

  const dailyBudget = budget.data?.daily_budget_usd ?? 0;
  const dailySpend = budget.data?.daily_spend_usd ?? 0;
  
  const modelData = (cost.data?.model_wise ?? [])
    .map((m: any) => ({ name: m.model, cost: Number(m.cost_usd.toFixed(4)) }))
    .sort((a: any, b: any) => b.cost - a.cost);

  return (
    <PageShell>
      <div className="mb-8">
        <h2 className="text-3xl font-bold tracking-tight text-foreground mb-2">Command Center</h2>
        <p className="text-sm text-muted-foreground">Live telemetry and governance overview.</p>
      </div>

      <motion.div 
        variants={{hidden: {}, show: { transition: { staggerChildren: 0.1 } }}} 
        initial="hidden" animate="show" 
        className="grid grid-cols-1 md:grid-cols-6 xl:grid-cols-12 gap-4 lg:gap-6 mb-8"
      >
        {/* Total Cost - Col Span 4 */}
        <div className="col-span-1 md:col-span-3 xl:col-span-4 flex">
          <MetricCard 
            variants={{hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }}}
            label="Total Compute Cost" 
            value={<AnimatedCounter value={cost.data?.total_spend_usd ?? 0} prefix="$" decimals={4} />} 
            sub="Across all AWS Bedrock APIs"
            icon={<Wallet size={20} />}
            className="w-full bg-gradient-to-br from-primary/10 via-transparent to-transparent border-primary/20 shadow-[0_0_40px_rgba(59,130,246,0.1)]"
          />
        </div>

        {/* Small Metrics Subgrid - Col Span 4 */}
        <div className="col-span-1 md:col-span-3 xl:col-span-4 grid grid-cols-2 gap-4 lg:gap-6">
          <MetricCard 
            variants={{hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 }}}
            label="Total Requests" 
            value={<AnimatedCounter value={metrics.data?.total_requests ?? 0} />} 
            sub={`${metrics.data?.failed_requests ?? 0} failed`}
            icon={<Activity size={18} />}
          />
          <MetricCard 
            variants={{hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 }}}
            label="Cache Hit Rate" 
            value={<AnimatedCounter value={(metrics.data?.cache_hit_rate ?? 0) * 100} suffix="%" decimals={1} />} 
            sub={`${cache.data?.entry_count ?? 0} entries`}
            icon={<Target size={18} />}
          />
          <MetricCard 
            variants={{hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 }}}
            label="Avg Latency" 
            value={<AnimatedCounter value={metrics.data?.avg_latency_ms ?? 0} suffix="ms" />} 
            sub="Avg Across"
            icon={<Clock size={18} />}
          />
          <MetricCard 
            variants={{hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 }}}
            label="Active Agents" 
            value={<AnimatedCounter value={activeAgentCount} />} 
            sub="FinOps & Red Team"
            icon={<Bot size={18} />}
          />
        </div>

        {/* Budget Utilization - Col Span 4 */}
        <div className="col-span-1 md:col-span-6 xl:col-span-4 flex">
          <Card className="w-full flex flex-col group">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Budget Utilization</CardTitle>
                  <CardDescription>Daily cap enforcement</CardDescription>
                </div>
                <div className="h-10 w-10 rounded-full bg-accent/20 flex items-center justify-center text-accent group-hover:scale-110 transition-transform">
                  <ShieldAlert size={18} />
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col justify-end pt-4 space-y-5">
              <div className="text-center relative">
                <div className="text-5xl font-extrabold tracking-tighter mb-1 gradient-text">
                  <AnimatedCounter value={dailySpend} prefix="$" decimals={2} />
                </div>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  of {formatUsd(dailyBudget, 0)} daily limit
                </p>
              </div>
              <Progress value={dailyBudget > 0 ? dailySpend / dailyBudget : 0} className="h-4 shadow-inner" />
              <div className="flex justify-between items-center pt-3 border-t border-border/60">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Kill Switch</p>
                <Badge tone={statusTone(budget.data?.kill_switch_mode)} className="px-3 py-1 text-[10px]">{budget.data?.kill_switch_mode || "Disabled"}</Badge>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Chart - Col Span 8 */}
        <div className="col-span-1 md:col-span-6 xl:col-span-8 flex h-[400px]">
          <Card className="w-full flex flex-col">
            <CardHeader>
              <CardTitle className="text-lg">Model-wise spend</CardTitle>
              <CardDescription>Accumulated cost per foundation model over time</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 min-h-[300px]">
              {modelData.length === 0 ? (
                <EmptyState title="No spend recorded" hint="Run a few playground queries to generate telemetry." />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={modelData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={theme === "dark" ? "#7c3aed" : "#3b82f6"} stopOpacity={0.6}/>
                        <stop offset="95%" stopColor={theme === "dark" ? "#06b6d4" : "#8b5cf6"} stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="name" fontSize={11} axisLine={false} tickLine={false} dy={10} stroke={theme === "dark" ? "rgba(255,255,255,0.4)" : "rgba(0,0,0,0.4)"} />
                    <YAxis fontSize={11} axisLine={false} tickLine={false} tickFormatter={(v: number) => `$${v}`} dx={-10} stroke={theme === "dark" ? "rgba(255,255,255,0.4)" : "rgba(0,0,0,0.4)"} />
                    <Tooltip 
                      formatter={(v) => formatUsd(Number(v), 4)} 
                      contentStyle={{ backgroundColor: theme === "dark" ? "rgba(15,20,30,0.9)" : "rgba(255,255,255,0.95)", backdropFilter: "blur(12px)", borderColor: theme === "dark" ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.05)", borderRadius: "16px", fontSize: "13px", padding: "12px 16px", boxShadow: theme === "dark" ? "0 20px 40px rgba(0,0,0,0.5)" : "0 20px 40px rgba(0,0,0,0.08)" }}
                      itemStyle={{ color: theme === "dark" ? "#fff" : "#0f172a", fontWeight: "bold" }}
                    />
                    <Area type="monotone" dataKey="cost" stroke={theme === "dark" ? "#a855f7" : "#6366f1"} strokeWidth={4} fillOpacity={1} fill="url(#colorGradient)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Pending Approvals & AI Recommendations - Col Span 4 */}
        <div className="col-span-1 md:col-span-6 xl:col-span-4 flex flex-col gap-4 lg:gap-6">
          <Card className="flex-1 flex flex-col">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Approvals</CardTitle>
                <Badge tone={(pending.data?.items ?? []).length > 0 ? "amber" : "gray"}>
                  {(pending.data?.items ?? []).length} pending
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="flex-1">
              {(pending.data?.items ?? []).length === 0 ? (
                <EmptyState title="All caught up" hint="No actions pending." icon={<CheckCircle2 size={24} />} />
              ) : (
                <div className="space-y-3">
                  {(pending.data?.items ?? []).slice(0,3).map((a: any) => (
                    <Link href="/approvals" key={a.action_id} className="block group">
                      <div className="p-3 rounded-xl border border-border/50 bg-muted/20 hover:bg-muted/50 hover:border-primary/30 transition-all">
                        <div className="flex justify-between items-start mb-2">
                          <p className="text-sm font-semibold group-hover:text-primary transition-colors">{a.title}</p>
                          <Badge tone={statusTone(a.risk_level === "low" ? "normal" : "critical")} className="text-[10px] uppercase">{a.risk_level}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground flex items-center justify-between">
                          <span>Est. Savings</span>
                          <span className="text-emerald-500 font-bold tabular">{formatUsd(a.expected_monthly_saving_usd, 2)}</span>
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="flex-1 flex flex-col bg-gradient-to-br from-accent/5 via-transparent to-transparent">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">AI Optimization</CardTitle>
            </CardHeader>
            <CardContent className="flex-1">
              {(budget.data?.recommendations ?? []).length === 0 ? (
                 <EmptyState title="Highly Optimized" hint="No new savings found." icon={<Zap size={24} />} />
              ) : (
                <div className="space-y-3">
                  {(budget.data?.recommendations ?? []).slice(0, 3).map((r: any) => (
                    <div key={r.action_id} className="flex items-center justify-between p-3 rounded-xl border border-border/40 bg-background/50 hover:shadow-md transition-shadow group">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-accent/15 flex items-center justify-center text-accent group-hover:scale-110 transition-transform">
                          <Zap size={14} />
                        </div>
                        <span className="font-semibold text-sm">{r.title}</span>
                      </div>
                      <span className="text-xs font-bold text-emerald-500 tabular">{formatUsd(r.expected_monthly_saving_usd, 0)}/mo</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

      </motion.div>
    </PageShell>
  );
}
