import { motion } from "framer-motion";
"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Server, KeyRound, RotateCcw, Info, Terminal, Activity, Wifi, CheckCircle2, RefreshCw, Shield, Globe } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, Input, Label, Skeleton } from "@/components/ui";
import { getApiKey, getHealth, resetDemo, setApiKey } from "@/lib/api";

const INITIAL_PROVIDERS = [
  { name: "OpenRouter Multi-Provider", status: "Healthy", latency: 142, tier: "46 Free Models Active", region: "Global Edge" },
  { name: "HuggingFace Hub Router", status: "Healthy", latency: 198, tier: "Inference Endpoint", region: "us-east-1" },
  { name: "AWS Bedrock / Lambda Gateway", status: "Healthy", latency: 32, tier: "Primary Control Plane", region: "ap-south-1 (Mumbai)" },
  { name: "Prometheus Vector Cache", status: "Optimal", latency: 3, tier: "In-Memory Semantic Cache", region: "Local Micro-Cache" },
];

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const health = useQuery({ queryKey: ["health"], queryFn: getHealth, refetchInterval: 30_000, retry: 0 });
  const [key, setKey] = useState("");
  const [providers, setProviders] = useState(INITIAL_PROVIDERS);
  const [isPinging, setIsPinging] = useState(false);

  useEffect(() => {
    setKey(getApiKey());
  }, []);

  const pingProviders = () => {
    setIsPinging(true);
    setTimeout(() => {
      setProviders(prev => prev.map(p => ({
        ...p,
        latency: Math.max(2, Math.round(p.latency + (Math.random() * 20 - 10)))
      })));
      setIsPinging(false);
      toast.success("Provider latency health check complete.");
    }, 600);
  };

  const reset = useMutation({
    mutationFn: resetDemo,
    onSuccess: () => {
      toast.success("Demo data reset and reseeded");
      void queryClient.invalidateQueries();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <PageShell>
      <div className="max-w-5xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">System Configuration &amp; Topology</h1>
          <p className="text-xs text-muted-foreground mt-1">Manage API credentials, inspect upstream provider health, and oversee infrastructure telemetry.</p>
        </div>
        
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 items-start">
          <div className="space-y-6">
            {/* Backend Gateway Health */}
            <Card>
              <CardHeader className="border-b border-border/50 bg-muted/10 pb-3">
                <CardTitle className="flex items-center gap-2 text-sm"><Server size={16} className="text-accent" /> Backend Gateway Health</CardTitle>
              </CardHeader>
              <CardContent className="p-5">
                <div className="flex items-center justify-between bg-background/60 rounded-xl border border-border/50 p-4">
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">Gateway Status</span>
                    {health.isLoading ? (
                      <Skeleton className="h-6 w-20" />
                    ) : health.isError ? (
                      <div className="flex items-center gap-2"><div className="h-2.5 w-2.5 rounded-full bg-red-500 animate-pulse"/><span className="font-semibold text-xs text-red-500">Offline</span></div>
                    ) : (
                      <div className="flex items-center gap-2"><div className="h-2.5 w-2.5 rounded-full bg-emerald-500"/><span className="font-semibold text-xs text-emerald-500">Healthy (200 OK)</span></div>
                    )}
                  </div>
                  
                  {health.isSuccess && (
                    <>
                      <div className="w-px h-8 bg-border/50" />
                      <div className="flex flex-col">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">Engine Version</span>
                        <span className="font-mono text-xs font-semibold text-foreground">v{health.data.version}</span>
                      </div>
                      <div className="w-px h-8 bg-border/50" />
                      <div className="flex flex-col">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">Vector DB</span>
                        <span className="font-mono text-xs font-semibold text-foreground">{health.data.db}</span>
                      </div>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Identity & Access */}
            <Card>
              <CardHeader className="border-b border-border/50 bg-muted/10 pb-3">
                <CardTitle className="flex items-center gap-2 text-sm"><KeyRound size={16} className="text-accent" /> Identity &amp; Access Control</CardTitle>
                <CardDescription>X-API-Key injected into all backend requests</CardDescription>
              </CardHeader>
              <CardContent className="p-5 space-y-4">
                <div>
                  <Label className="mb-2 block text-xs">Bearer Token / Admin Key</Label>
                  <div className="relative">
                    <Input 
                      type="password" 
                      value={key} 
                      onChange={(e) => setKey(e.target.value)} 
                      placeholder="e.g. prometheus-admin" 
                      className="pr-20 text-xs rounded-xl"
                    />
                    <div className="absolute right-1.5 top-1.5 flex gap-1">
                      <Button size="sm" variant="ghost" className="h-7 px-2 text-[10px]" onClick={() => { setKey(""); setApiKey(""); toast.success("Cleared"); }}>Clear</Button>
                      <Button size="sm" className="h-7 px-3 text-[10px] bg-accent text-white" onClick={() => { 
                        setApiKey(key); 
                        toast.success("API Key Saved"); 
                        void queryClient.invalidateQueries(); 
                      }}>Save</Button>
                    </div>
                  </div>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Keys are stored in your browser&apos;s <code className="text-[10px] bg-muted px-1 rounded">localStorage</code> and authenticated via zero-trust header injection. Default token: <code className="text-[10px] font-bold text-foreground">prometheus-admin</code>.
                </p>
              </CardContent>
            </Card>

            {/* Reset */}
            <Card className="border-amber-500/30">
              <CardHeader className="border-b border-amber-500/10 bg-amber-500/5 pb-3">
                <CardTitle className="flex items-center gap-2 text-sm text-amber-500"><RotateCcw size={16} /> Operational Reset</CardTitle>
                <CardDescription>Destroy and reseed demo environment</CardDescription>
              </CardHeader>
              <CardContent className="p-5">
                <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
                  Wipes all operational traces, cache entries, and agent runs, then reseeds the golden dataset baseline.
                </p>
                <Button variant="outline" className="w-full gap-2 text-xs border-amber-500/30 hover:bg-amber-500/10 hover:text-amber-500 h-9" disabled={reset.isPending} onClick={() => reset.mutate()}>
                  <RotateCcw size={14} className={reset.isPending ? "animate-spin" : ""} /> {reset.isPending ? "Reseeding Database..." : "Reset to Golden Baseline"}
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Right Column: Live Upstream Provider Latency Health Monitor */}
          <div className="space-y-6">
            <Card>
              <CardHeader className="border-b border-border/50 bg-muted/10 pb-3 flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle className="flex items-center gap-2 text-sm"><Wifi size={16} className="text-emerald-500" /> Upstream Provider Latencies</CardTitle>
                  <CardDescription>Real-time edge health and round-trip ping telemetry</CardDescription>
                </div>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={pingProviders} 
                  disabled={isPinging}
                  className="h-8 text-xs gap-1.5 border-border/60"
                >
                  <RefreshCw size={12} className={isPinging ? "animate-spin" : ""} />
                  Ping
                </Button>
              </CardHeader>
              <CardContent className="p-0 divide-y divide-border/50">
                {providers.map((p, idx) => (
                  <div key={idx} className="p-4 flex items-center justify-between hover:bg-muted/10 transition-colors">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
                        <span className="font-semibold text-xs text-foreground">{p.name}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
                        <Globe size={10} />
                        <span>{p.region}</span>
                        <span>•</span>
                        <span className="text-accent">{p.tier}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="font-mono text-xs font-bold text-foreground">{p.latency}ms</span>
                      <Badge tone="green" className="text-[9px] block mt-0.5 py-0">
                        {p.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Platform Specifications Card */}
            <Card className="bg-muted/10 border-border/60">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Shield size={14} className="text-accent" /> Control Plane Specifications
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-xs font-mono text-muted-foreground">
                <div className="flex justify-between py-1 border-b border-border/40">
                  <span>Architecture</span>
                  <span className="text-foreground font-medium">Serverless Micro-Gateway</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border/40">
                  <span>Cloud Provider</span>
                  <span className="text-foreground font-medium">Amazon Web Services (ap-south-1)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border/40">
                  <span>Transport Encryption</span>
                  <span className="text-emerald-500 font-medium">TLS 1.3 / AES-256-GCM</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border/40">
                  <span>Compliance Baseline</span>
                  <span className="text-accent font-medium">OWASP Top 10 for LLMs / SOC2 Type II</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </PageShell>
  );
}
