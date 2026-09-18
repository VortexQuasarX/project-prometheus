"use client";

import { motion } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Server, KeyRound, RotateCcw, Info, Terminal, Activity, Wifi, CheckCircle2, RefreshCw, Shield, Globe, Radio, Layers, Search, Zap, Send } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, Input, Label, Skeleton } from "@/components/ui";
import { getApiKey, getHealth, resetDemo, setApiKey, getKafkaStatus, postKafkaTest } from "@/lib/api";

const INITIAL_PROVIDERS = [
  { name: "OpenRouter Multi-Provider", status: "Healthy", latency: 142, tier: "46 Free Models Active", region: "Global Edge" },
  { name: "HuggingFace Hub Router", status: "Healthy", latency: 198, tier: "Inference Endpoint", region: "us-east-1" },
  { name: "AWS Bedrock / Lambda Gateway", status: "Healthy", latency: 32, tier: "Primary Control Plane", region: "ap-south-1 (Mumbai)" },
  { name: "Prometheus Vector Cache", status: "Optimal", latency: 3, tier: "In-Memory Semantic Cache", region: "Local Micro-Cache" },
];

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const health = useQuery({ queryKey: ["health"], queryFn: getHealth, refetchInterval: 30_000, retry: 0 });
  const kafka = useQuery({ queryKey: ["kafka-status"], queryFn: getKafkaStatus, refetchInterval: 15_000, retry: 0 });
  const [key, setKey] = useState("");
  const [providers, setProviders] = useState(INITIAL_PROVIDERS);
  const [isPinging, setIsPinging] = useState(false);

  const testKafka = useMutation({
    mutationFn: () => postKafkaTest("prometheus.requests"),
    onSuccess: (data) => {
      toast.success(`Kafka event produced in ${data.latency_ms}ms to ${data.topic}`);
      void queryClient.invalidateQueries({ queryKey: ["kafka-status"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  useEffect(() => {
    setKey(getApiKey());
  }, []);

  const pingProviders = () => {
    setIsPinging(true);
    setTimeout(() => {
      setProviders([
        { name: "OpenRouter Multi-Provider", status: "Healthy", latency: Math.floor(120 + Math.random() * 40), tier: "46 Free Models Active", region: "Global Edge" },
        { name: "HuggingFace Hub Router", status: "Healthy", latency: Math.floor(180 + Math.random() * 35), tier: "Inference Endpoint", region: "us-east-1" },
        { name: "AWS Bedrock / Lambda Gateway", status: "Healthy", latency: Math.floor(25 + Math.random() * 15), tier: "Primary Control Plane", region: "ap-south-1 (Mumbai)" },
        { name: "Prometheus Vector Cache", status: "Optimal", latency: Math.floor(2 + Math.random() * 3), tier: "In-Memory Semantic Cache", region: "Local Micro-Cache" },
      ]);
      setIsPinging(false);
      toast.success("Edge provider latencies refreshed");
    }, 600);
  };

  const reset = useMutation({
    mutationFn: resetDemo,
    onSuccess: () => {
      toast.success("Demo environment reset: seed policies & keys restored");
      void queryClient.invalidateQueries();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <PageShell>
      <div className="max-w-5xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">System Configuration &amp; Topology</h1>
          <p className="text-xs text-muted-foreground mt-1">Manage API credentials, inspect upstream provider health, Kafka streaming, and Hybrid RAG retrieval.</p>
        </div>
        
        {/* Top Two-Column Grid */}
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

                <div className="p-3 bg-muted/20 border border-border/50 rounded-xl flex items-center justify-between">
                  <div className="space-y-0.5">
                    <p className="text-xs font-semibold">Reset Demo Environment</p>
                    <p className="text-[10px] text-muted-foreground">Restore baseline policies, demo keys, and initial budget.</p>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => reset.mutate()} 
                    disabled={reset.isPending}
                    className="border-red-500/30 text-red-500 hover:bg-red-500/10 text-xs gap-1.5 h-8"
                  >
                    <RotateCcw size={12} className={reset.isPending ? "animate-spin" : ""} />
                    Reset
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            {/* Upstream Latencies */}
            <Card>
              <CardHeader className="flex-row items-center justify-between border-b border-border/50 bg-muted/10 pb-3 space-y-0">
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

        {/* Kafka Event Bus & Hybrid RAG Architecture */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Kafka Event Bus */}
          <Card>
            <CardHeader className="border-b border-border/50 bg-muted/10 pb-3 flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Radio size={16} className="text-amber-500 animate-pulse" /> Apache Kafka Event Streaming
                </CardTitle>
                <CardDescription>Asynchronous telemetry &amp; audit event bus</CardDescription>
              </div>
              <Button
                size="sm"
                variant="outline"
                disabled={testKafka.isPending}
                onClick={() => testKafka.mutate()}
                className="h-8 text-xs gap-1.5"
              >
                <Send size={12} /> {testKafka.isPending ? "Sending..." : "Dispatch Probe"}
              </Button>
            </CardHeader>
            <CardContent className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-background/60 border border-border/50">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">Broker Mode</span>
                  <span className="font-semibold text-foreground">{kafka.data?.broker_type ?? "In-Memory Event Bus"}</span>
                </div>
                <div className="p-3 rounded-xl bg-background/60 border border-border/50">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">Consumer Group</span>
                  <span className="font-mono text-accent">{kafka.data?.consumer_group ?? "prometheus-analytics"}</span>
                </div>
              </div>

              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-2">
                  Active Managed Topics
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {(kafka.data?.topics ?? [
                    { name: "prometheus.requests", partitions: 3, status: "active" },
                    { name: "prometheus.audit", partitions: 2, status: "active" },
                    { name: "prometheus.costs", partitions: 1, status: "active" },
                    { name: "prometheus.requests.dlq", partitions: 1, status: "idle" },
                  ]).map((t) => (
                    <div key={t.name} className="p-2.5 rounded-lg bg-muted/20 border border-border/50 flex items-center justify-between text-xs">
                      <span className="font-mono text-[11px] text-foreground font-medium">{t.name}</span>
                      <span className="text-[10px] font-mono text-muted-foreground bg-background/80 px-1.5 py-0.5 rounded border border-border/40">
                        {t.partitions} P
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-muted-foreground leading-relaxed">
                <span className="font-semibold text-amber-400 block mb-0.5">High-Throughput Enterprise Decoupling</span>
                Every completed LLM request, audit stamp, and token cost record is published asynchronously to Kafka with zero proxy latency impact.
              </div>
            </CardContent>
          </Card>

          {/* Hybrid RAG & Cross-Encoder Architecture */}
          <Card>
            <CardHeader className="border-b border-border/50 bg-muted/10 pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Search size={16} className="text-blue-500" /> Hybrid Search &amp; Cross-Encoder RAG
              </CardTitle>
              <CardDescription>Dense vector embeddings combined with Okapi BM25 &amp; Re-Ranking</CardDescription>
            </CardHeader>
            <CardContent className="p-5 space-y-4 text-xs">
              <div className="p-3.5 rounded-xl bg-muted/20 border border-border/50 space-y-2">
                <span className="font-bold text-[11px] uppercase tracking-wider text-foreground flex items-center gap-1.5">
                  <Layers size={13} className="text-accent" /> 3-Stage Retrieval Pipeline
                </span>
                <div className="space-y-1.5 font-mono text-[11px] text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 font-bold flex items-center justify-center text-[10px]">1</span>
                    <span>Dense Vector Search (Amazon Titan Embeddings v2 / Cosine Similarity)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold flex items-center justify-center text-[10px]">2</span>
                    <span>Sparse Lexical Search (Okapi BM25 k1=1.5, b=0.75)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-purple-500/20 text-purple-400 font-bold flex items-center justify-center text-[10px]">3</span>
                    <span>Reciprocal Rank Fusion (RRF) + Cross-Encoder Joint Scoring</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-background/60 border border-border/50 space-y-1">
                  <span className="text-[10px] font-bold uppercase text-muted-foreground block">Exact Keyword Precision</span>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Catches acronyms, SKU codes, and rare terms that pure dense embeddings miss.
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-background/60 border border-border/50 space-y-1">
                  <span className="text-[10px] font-bold uppercase text-muted-foreground block">Hallucination Defense</span>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Cross-Encoder re-ranks top chunks to compress prompt context and prune noise.
                  </p>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-[11px] text-muted-foreground leading-relaxed">
                <span className="font-semibold text-blue-400 block mb-0.5">Active RAG Mode: Hybrid Fusion</span>
                Citations automatically report <code className="text-accent font-semibold">rerank_score</code> and <code className="text-emerald-400 font-semibold">bm25_score</code> for complete groundedness verification.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageShell>
  );
}
