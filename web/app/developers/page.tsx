"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui";
import { Code2, Terminal, Copy, Check, Sparkles, BookOpen, Layers, Zap, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

const PYTHON_CODE = `import os
from prometheus import PrometheusClient

# Initialize the Prometheus client with drop-in OpenAI parity
client = PrometheusClient(
    api_key=os.environ.get("PROMETHEUS_API_KEY", "prometheus-admin"),
    base_url="https://w6qubbix87.execute-api.ap-south-1.amazonaws.com/api/v1"
)

# Automated governance, FinOps caching & semantic routing happens automatically
response = client.chat.completions.create(
    model="auto-router",  # Automatically chooses best model for cost & quality
    messages=[
        {"role": "system", "content": "You are a specialized enterprise AI assistant."},
        {"role": "user", "content": "Analyze our AWS CloudWatch bill for anomalies."}
    ],
    temperature=0.2,
    stream=True  # Real-time token streaming with sub-100ms TTFT
)

for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")
`;

const TYPESCRIPT_CODE = `import { Prometheus } from "@prometheus-ai/sdk";

const prometheus = new Prometheus({
  apiKey: process.env.PROMETHEUS_API_KEY || "prometheus-admin",
  baseUrl: "https://w6qubbix87.execute-api.ap-south-1.amazonaws.com/api/v1"
});

async function main() {
  // Execute via Prometheus intelligent proxy with micro-dollar caching
  const completion = await prometheus.chat.completions.create({
    model: "llama-3.3-70b-instruct:free",
    messages: [
      { role: "user", content: "Optimize this PostgreSQL query plan for high throughput." }
    ],
    governance: {
      requireCache: true,      // 0-cost vector similarity lookup
      piiMasking: true,        // Reversible zero-trust entity tokenization
      injectionDefense: true   // Pre-flight heuristic prompt injection guard
    }
  });

  console.log("Response:", completion.choices[0].message.content);
  console.log("Telemetry:", completion._telemetry); // Latency, Cost, Judge Score
}

main();
`;

const CURL_CODE = `curl -X POST https://w6qubbix87.execute-api.ap-south-1.amazonaws.com/api/v1/chat \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: prometheus-admin" \\
  -d '{
    "query": "What are the primary cost drivers in modern agentic architectures?",
    "model": "deepseek-r1:free"
  }'`;

const CLI_CMDS = [
  { cmd: "prometheus init", desc: "Initialize local project configuration and link API keys." },
  { cmd: "prometheus test --arena", desc: "Run a head-to-head dual-model benchmark from terminal." },
  { cmd: "prometheus traces --tail -n 20", desc: "Stream live production request traces in real-time." },
  { cmd: "prometheus kill-switch --engage", desc: "Emergency circuit-breaker to halt all LLM egress traffic." },
  { cmd: "prometheus redteam --fuzz-all", desc: "Execute automated OWASP Top 10 jailbreak fuzzing." }
];

export default function DevelopersPage() {
  const [activeTab, setActiveTab] = useState<"python" | "typescript" | "curl">("python");
  const [copied, setCopied] = useState(false);

  const getCode = () => {
    if (activeTab === "python") return PYTHON_CODE;
    if (activeTab === "typescript") return TYPESCRIPT_CODE;
    return CURL_CODE;
  };

  const copyCode = () => {
    navigator.clipboard.writeText(getCode());
    setCopied(true);
    toast.success("Code snippet copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <PageShell>
      <div className="space-y-6 max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/50 pb-5">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                <Code2 className="text-accent" size={24} /> Developer Ecosystem &amp; SDKs
              </h1>
              <Badge tone="green" className="text-[10px]">v1.4.0 Production</Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Drop-in OpenAI SDK replacements, TypeScript libraries, and CLI utilities for zero-friction integration.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-muted-foreground">Endpoint:</span>
            <code className="bg-muted px-2 py-1 rounded border border-border/50 text-foreground">/api/v1/chat</code>
          </div>
        </div>

        {/* Code & SDK Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* Main Code Viewer */}
          <Card className="lg:col-span-2 flex flex-col">
            <CardHeader className="p-3 border-b border-border/50 bg-muted/10 flex-row items-center justify-between space-y-0">
              <div className="flex items-center gap-1.5 bg-background/60 p-1 rounded-xl border border-border/50">
                <button
                  onClick={() => setActiveTab("python")}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    activeTab === "python" ? "bg-accent text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Python (OpenAI Drop-In)
                </button>
                <button
                  onClick={() => setActiveTab("typescript")}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    activeTab === "typescript" ? "bg-accent text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  TypeScript / Node.js
                </button>
                <button
                  onClick={() => setActiveTab("curl")}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    activeTab === "curl" ? "bg-accent text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  cURL
                </button>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={copyCode}
                className="h-8 text-xs gap-1.5 border-border/60"
              >
                {copied ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                {copied ? "Copied" : "Copy Code"}
              </Button>
            </CardHeader>

            <CardContent className="p-0 bg-black/40 overflow-x-auto">
              <pre className="p-4 text-xs font-mono text-zinc-300 leading-relaxed overflow-x-auto">
                <code>{getCode()}</code>
              </pre>
            </CardContent>
          </Card>

          {/* Quickstart & Packages */}
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-3 border-b border-border/50 bg-muted/10">
                <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Layers size={14} className="text-accent" /> Installation Packages
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                <div className="p-2.5 rounded-xl bg-muted/20 border border-border/50 space-y-1">
                  <span className="text-[10px] text-muted-foreground uppercase font-bold">Python Package</span>
                  <div className="flex items-center justify-between text-xs font-mono">
                    <code>pip install prometheus-ai</code>
                    <button onClick={() => { navigator.clipboard.writeText("pip install prometheus-ai"); toast.success("Copied"); }} className="text-muted-foreground hover:text-foreground">
                      <Copy size={12} />
                    </button>
                  </div>
                </div>

                <div className="p-2.5 rounded-xl bg-muted/20 border border-border/50 space-y-1">
                  <span className="text-[10px] text-muted-foreground uppercase font-bold">Node.js Package</span>
                  <div className="flex items-center justify-between text-xs font-mono">
                    <code>npm install @prometheus-ai/sdk</code>
                    <button onClick={() => { navigator.clipboard.writeText("npm install @prometheus-ai/sdk"); toast.success("Copied"); }} className="text-muted-foreground hover:text-foreground">
                      <Copy size={12} />
                    </button>
                  </div>
                </div>

                <div className="p-2.5 rounded-xl bg-muted/20 border border-border/50 space-y-1">
                  <span className="text-[10px] text-muted-foreground uppercase font-bold">Global CLI</span>
                  <div className="flex items-center justify-between text-xs font-mono">
                    <code>brew install prometheus-cli</code>
                    <button onClick={() => { navigator.clipboard.writeText("brew install prometheus-cli"); toast.success("Copied"); }} className="text-muted-foreground hover:text-foreground">
                      <Copy size={12} />
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-accent/5 via-purple-500/5 to-emerald-500/5 border-accent/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-accent">
                  <ShieldCheck size={14} /> Zero Code Changes
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-xs text-muted-foreground">
                <p>
                  Prometheus acts as an <strong>OpenAI-compatible reverse proxy</strong>.
                </p>
                <p>
                  Simply swap your API base URL to Prometheus to instantly gain multi-model routing, FinOps semantic caching, and real-time guardrails with zero application refactoring.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* CLI Reference Table */}
        <Card>
          <CardHeader className="border-b border-border/50 bg-muted/10 pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Terminal size={16} className="text-accent" /> Prometheus CLI Command Reference
            </CardTitle>
            <CardDescription>Command-line interface for engineers, DevOps, and automation pipelines</CardDescription>
          </CardHeader>
          <CardContent className="p-0 divide-y divide-border/50">
            {CLI_CMDS.map((c, i) => (
              <div key={i} className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-muted/10 transition-colors">
                <div className="flex items-center gap-2 font-mono text-xs text-accent font-semibold">
                  <span className="text-muted-foreground select-none">$</span>
                  <code>{c.cmd}</code>
                </div>
                <span className="text-xs text-muted-foreground">{c.desc}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </PageShell>
  );
}
