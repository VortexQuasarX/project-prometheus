"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui";
import { Building2, Users, CreditCard, Shield, Download, Plus, CheckCircle2, DollarSign, PieChart } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { formatUsd } from "@/lib/utils";
import { toast } from "sonner";
import { getBudget, getCostReport } from "@/lib/api";

interface Department {
  id: string;
  name: string;
  members: number;
  dailySpend: number;
  dailyQuota: number;
  modelsAllowed: string[];
  owner: string;
}

const BASE_DEPARTMENTS: Department[] = [
  { id: "dept-1", name: "Core Engineering", members: 24, dailySpend: 0.85, dailyQuota: 50.0, modelsAllowed: ["bedrock-cheap", "qwen.qwen3-coder-480b-a35b-v1:0"], owner: "alex@prometheus.internal" },
  { id: "dept-2", name: "Data Science & ML", members: 12, dailySpend: 1.40, dailyQuota: 80.0, modelsAllowed: ["meta.llama3-8b-instruct-v1:0", "us.meta.llama3-3-70b-instruct-v1:0"], owner: "elena@prometheus.internal" },
  { id: "dept-3", name: "FinOps & Governance", members: 6, dailySpend: 0.35, dailyQuota: 25.0, modelsAllowed: ["apac.amazon.nova-micro-v1:0", "mock-small"], owner: "marcus@prometheus.internal" },
  { id: "dept-4", name: "Autonomous Systems", members: 18, dailySpend: 0.65, dailyQuota: 40.0, modelsAllowed: ["apac.amazon.nova-lite-v1:0", "us.deepseek.r1-v1:0"], owner: "sarah@prometheus.internal" },
];

export default function WorkspacesPage() {
  const budget = useQuery({ queryKey: ["budget"], queryFn: getBudget, refetchInterval: 30000 });
  const liveDailySpend = budget.data?.daily_spend_usd ?? 0.85;

  const departments: Department[] = BASE_DEPARTMENTS.map(d => {
    if (d.id === "dept-1") {
      return { ...d, dailySpend: Number(liveDailySpend.toFixed(4)) };
    }
    return d;
  });

  const [selectedDept, setSelectedDept] = useState<string>("dept-1");

  const active = departments.find(d => d.id === selectedDept) || departments[0];
  const totalSpend = departments.reduce((acc, d) => acc + d.dailySpend, 0);
  const totalQuota = departments.reduce((acc, d) => acc + d.dailyQuota, 0);

  const downloadChargebackInvoice = () => {
    const csvRows = [
      ["Department Name", "Owner", "Team Size", "Current Spend ($)", "Daily Quota ($)", "Quota Utilization (%)"],
      ...departments.map(d => [
        d.name,
        d.owner,
        d.members.toString(),
        d.dailySpend.toFixed(2),
        d.dailyQuota.toFixed(2),
        ((d.dailySpend / d.dailyQuota) * 100).toFixed(1) + "%"
      ])
    ];

    const csvContent = "data:text/csv;charset=utf-8," + csvRows.map(r => r.map(c => `"${c}"`).join(",")).join("\n");
    const link = document.createElement("a");
    link.setAttribute("href", encodeURI(csvContent));
    link.setAttribute("download", `prometheus-finops-chargeback-${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success("Departmental chargeback statement downloaded.");
  };

  return (
    <PageShell>
      <div className="space-y-6 max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/50 pb-5">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                <Building2 className="text-accent" size={24} /> Multi-Tenant Workspaces &amp; Chargeback
              </h1>
              <Badge tone="blue" className="text-[10px]">Enterprise Orgs</Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Partition LLM spend, enforce departmental quotas, and generate itemized monthly chargeback statements.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={downloadChargebackInvoice} className="h-9 text-xs gap-1.5 border-border/60">
              <Download size={13} /> Export Chargeback CSV
            </Button>
            <Button size="sm" onClick={() => toast.info("Contact Prometheus Admin to provision new tenant organizations.")} className="h-9 text-xs gap-1.5 bg-accent text-white">
              <Plus size={13} /> New Workspace
            </Button>
          </div>
        </div>

        {/* Global FinOps Allocation Banner */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card className="bg-background/50">
            <CardContent className="p-4">
              <p className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">Active Workspaces</p>
              <p className="font-mono text-xl font-bold text-foreground">{departments.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-background/50">
            <CardContent className="p-4">
              <p className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">Total Team Members</p>
              <p className="font-mono text-xl font-bold text-foreground">{departments.reduce((a, d) => a + d.members, 0)}</p>
            </CardContent>
          </Card>
          <Card className="bg-background/50">
            <CardContent className="p-4">
              <p className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">Aggregated Daily Spend</p>
              <p className="font-mono text-xl font-bold text-accent">${totalSpend.toFixed(2)}</p>
            </CardContent>
          </Card>
          <Card className="bg-background/50">
            <CardContent className="p-4">
              <p className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">Daily Cap Utilization</p>
              <p className="font-mono text-xl font-bold text-emerald-500">{((totalSpend / totalQuota) * 100).toFixed(1)}%</p>
            </CardContent>
          </Card>
        </div>

        {/* Workspaces List & Detail Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* Workspaces Selector List */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Department Workspaces</h3>
            {departments.map((d) => {
              const isSelected = selectedDept === d.id;
              const utilPct = Math.round((d.dailySpend / d.dailyQuota) * 100);

              return (
                <div
                  key={d.id}
                  onClick={() => setSelectedDept(d.id)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                    isSelected
                      ? "bg-accent/10 border-accent/40 shadow-sm"
                      : "bg-background/60 hover:bg-muted/30 border-border/50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Building2 size={16} className={isSelected ? "text-accent" : "text-muted-foreground"} />
                      <span className="font-bold text-sm text-foreground">{d.name}</span>
                    </div>
                    <Badge tone={utilPct > 80 ? "amber" : "green"} className="text-[10px] font-mono">
                      {utilPct}% Quota
                    </Badge>
                  </div>
                  <div className="flex justify-between text-[11px] text-muted-foreground font-mono">
                    <span>Spend: ${d.dailySpend.toFixed(2)} / ${d.dailyQuota.toFixed(2)}</span>
                    <span>{d.members} members</span>
                  </div>
                  <div className="mt-2 h-1.5 w-full bg-muted/40 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${utilPct > 80 ? "bg-amber-500" : "bg-accent"} transition-all`}
                      style={{ width: `${Math.min(100, utilPct)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Active Workspace Detailed Inspector */}
          <Card className="lg:col-span-2 flex flex-col border-accent/20">
            <CardHeader className="border-b border-border/50 bg-muted/10 pb-3 flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <Shield size={18} className="text-accent" /> {active.name} Policy Quota
                </CardTitle>
                <CardDescription>Departmental governance rules, RBAC, and model permissions</CardDescription>
              </div>
              <Badge tone="green">Active</Badge>
            </CardHeader>

            <CardContent className="p-6 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-muted/20 rounded-xl border border-border/50">
                  <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">Primary Owner</span>
                  <span className="text-xs font-mono font-medium text-foreground">{active.owner}</span>
                </div>
                <div className="p-3 bg-muted/20 rounded-xl border border-border/50">
                  <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">Monthly Cost Projection</span>
                  <span className="text-xs font-mono font-bold text-accent">${(active.dailySpend * 30).toFixed(2)}/mo</span>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Whitelisted Foundation Models</h4>
                <div className="flex flex-wrap gap-2">
                  {active.modelsAllowed.map((m, i) => (
                    <Badge key={i} tone="gray" className="font-mono text-xs px-2.5 py-1">
                      {m}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-muted/10 border border-border/50 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                  <CheckCircle2 size={14} className="text-emerald-500" /> Automated FinOps Cost Caps Active
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  If this department reaches ${active.dailyQuota.toFixed(2)} in a single 24-hour cycle, Prometheus automatically shifts non-critical egress to 0-cost free models before activating the departmental circuit-breaker.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageShell>
  );
}
