"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell
} from "recharts";
import { motion } from "framer-motion";
import { Activity, Zap, CheckCircle2, AlertCircle, ArrowRight, Wallet, Target, Clock } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, MetricCard, Progress, Skeleton, statusTone, Table, Td, Th, AnimatedCounter } from "@/components/ui";
import { getBudget, getCacheStats, getCostReport, getMetrics, getPendingActions } from "@/lib/api";
import { formatMs, formatPercent, formatUsd } from "@/lib/utils";

export default function DashboardPage() {
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: getMetrics, refetchInterval: 30_000, retry: 0 });
  const cost = useQuery({ queryKey: ["cost-report"], queryFn: getCostReport, refetchInterval: 30_000, retry: 0 });
  const cache = useQuery({ queryKey: ["cache-stats"], queryFn: getCacheStats, refetchInterval: 30_000, retry: 0 });
  const budget = useQuery({ queryKey: ["budget"], queryFn: getBudget, refetchInterval: 30_000, retry: 0 });
  const pending = useQuery({ queryKey: ["pending-actions"], queryFn: getPendingActions, refetchInterval: 20_000, retry: 0 });

  const modelData = (cost.data?.model_wise ?? []).map((m) => ({ name: m.model, cost: Number(m.cost_usd.toFixed(4)) }));
  const dailyBudget = budget.data?.daily_budget_usd ?? 1;
  const dailySpend = budget.data?.daily_spend_usd ?? 0;
  
  // Custom colors for chart based on cost magnitude
  const getBarColor = (value: number) => {
    if (value > dailyBudget * 0.5) return "hsl(0, 72%, 51%)"; // destructive
    if (value > dailyBudget * 0.2) return "hsl(38, 92%, 50%)"; // warning
    return "url(#colorGradient)"; // primary gradient
  };

  return (
    <PageShell>
      <motion.div variants={{hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } }}} initial="hidden" animate="show" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {metrics.isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32" />)
        ) : metrics.isError ? (
          <motion.div variants={{hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }}} className="md:col-span-2 lg:col-span-4">
            <EmptyState title="Backend Offline" hint="Start the API using `make api` — displaying cached layout." icon={<AlertCircle size={48} />} />
          </motion.div>
        ) : (
          <>
            <MetricCard 
              variants={{hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }}}
              label="Total Cost" 
              value={<AnimatedCounter value={metrics.data?.total_cost_usd ?? 0} prefix="$" decimals={4} />} 
              sub={<span>cache saved <span className="text-emerald-500 font-semibold">{formatUsd(cost.data?.cache_savings_usd, 4)}</span></span>}
              icon={<Wallet size={20} />}
              gradient
            />
            <MetricCard 
              variants={{hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }}}
              label="Total Requests" 
              value={<AnimatedCounter value={metrics.data?.total_requests ?? 0} />} 
              sub={`${metrics.data?.failed_requests ?? 0} failed requests`}
              icon={<Activity size={20} />}
            />
            <MetricCard 
              variants={{hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }}}
              label="Cache Hit Rate" 
              value={<AnimatedCounter value={(metrics.data?.cache_hit_rate ?? 0) * 100} suffix="%" decimals={1} />} 
              sub={`${cache.data?.entry_count ?? 0} active entries`}
              icon={<Target size={20} />}
            />
            <MetricCard 
              variants={{hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }}}
              label="Avg Latency" 
              value={<AnimatedCounter value={metrics.data?.avg_latency_ms ?? 0} suffix=" ms" />} 
              sub="across all providers"
              icon={<Clock size={20} />}
            />
          </>
        )}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle>Budget utilization</CardTitle>
            <CardDescription>Daily cap enforcement</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col justify-center space-y-6">
            {budget.isLoading ? <Skeleton className="h-32" /> : (
              <>
                <div className="text-center">
                  <div className="text-4xl font-bold tracking-tight mb-2">
                    <AnimatedCounter value={dailySpend} prefix="$" decimals={4} />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    of <span className="text-foreground font-medium">{formatUsd(dailyBudget, 2)}</span> daily budget
                  </p>
                </div>
                
                <Progress value={dailyBudget > 0 ? dailySpend / dailyBudget : 0} className="h-3" />
                
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border/50">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Monthly Trend</p>
                    <p className="font-semibold">{formatUsd(budget.data?.monthly_spend_usd, 2)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Kill Switch</p>
                    <Badge tone={statusTone(budget.data?.kill_switch_mode)}>{budget.data?.kill_switch_mode}</Badge>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <motion.div initial={{opacity:0, scale:0.98}} animate={{opacity:1, scale:1}} transition={{duration:0.5, delay:0.2}} className="lg:col-span-2 relative">
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="text-xl">Model-wise spend</CardTitle>
              <CardDescription>Accumulated cost per foundation model</CardDescription>
            </CardHeader>
            <CardContent className="h-72">
              {modelData.length === 0 ? (
                <EmptyState title="No spend recorded" hint="Run a few playground queries to generate telemetry." />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={modelData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.5}/>
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                      </linearGradient>
                      <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="4" result="blur" />
                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                      </filter>
                    </defs>
                    <XAxis dataKey="name" fontSize={11} axisLine={false} tickLine={false} dy={10} stroke="rgba(255,255,255,0.4)" />
                    <YAxis fontSize={11} axisLine={false} tickLine={false} tickFormatter={(v: number) => `$${v}`} dx={-10} stroke="rgba(255,255,255,0.4)" />
                    <Tooltip 
                      formatter={(v) => formatUsd(Number(v), 4)} 
                      contentStyle={{ backgroundColor: 'rgba(15,20,30,0.8)', backdropFilter: 'blur(10px)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '12px', fontSize: '13px', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}
                      itemStyle={{ color: '#fff' }}
                    />
                    <Area type="monotone" dataKey="cost" stroke="url(#colorGradient)" strokeWidth={3} fillOpacity={1} fill="url(#colorGradient)" filter="url(#glow)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle>Pending Approvals</CardTitle>
              <CardDescription>Human-in-the-loop governance</CardDescription>
            </div>
            <Badge tone={(pending.data?.items ?? []).length > 0 ? "amber" : "gray"}>
              {(pending.data?.items ?? []).length} pending
            </Badge>
          </CardHeader>
          <CardContent>
            {(pending.data?.items ?? []).length === 0 ? (
              <EmptyState title="All caught up" hint="No FinOps actions waiting for approval." icon={<CheckCircle2 size={32} />} />
            ) : (
              <Table>
                <thead><tr><Th>Action</Th><Th className="text-right">Est. Savings</Th><Th>Risk</Th></tr></thead>
                <tbody>
                  {(pending.data?.items ?? []).map((a) => (
                    <tr key={a.action_id} className="border-t border-border/50 hover:bg-muted/30 transition-colors">
                      <Td><Link className="text-accent font-medium hover:underline flex items-center gap-2" href="/approvals">{a.title} <ArrowRight size={14} /></Link></Td>
                      <Td className="tabular text-right text-emerald-500 font-medium">{formatUsd(a.expected_monthly_saving_usd, 2)}</Td>
                      <Td><Badge tone={statusTone(a.risk_level === "low" ? "normal" : "critical")}>{a.risk_level}</Badge></Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Optimization Recommendations</CardTitle>
            <CardDescription>Live insights from FinOps agent telemetry</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {(budget.data?.recommendations ?? []).slice(0, 4).map((r, i) => (
              <div key={r.action_id} className="flex items-center justify-between rounded-xl bg-background border border-border/40 p-4 shadow-sm hover:shadow-md transition-shadow group">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center text-accent group-hover:scale-110 transition-transform">
                    <Zap size={16} />
                  </div>
                  <span className="font-medium text-sm">{r.title}</span>
                </div>
                <Badge tone="green" className="tabular">{formatUsd(r.expected_monthly_saving_usd, 2)}/mo</Badge>
              </div>
            ))}
            {(budget.data?.recommendations ?? []).length === 0 ? (
               <EmptyState title="Architecture Optimized" hint="The FinOps agent hasn't identified any new savings." icon={<Zap size={32} />} />
            ) : null}
          </CardContent>
        </Card>
      </div>
    </PageShell>
  );
}
