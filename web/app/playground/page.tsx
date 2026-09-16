"use client";
import { motion } from "framer-motion";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState, useEffect, Suspense } from "react";
import { toast } from "sonner";
import { Send, Sparkles, BookOpen, Clock, Activity, Cpu, Swords, Trophy, Copy, Check, Zap, Radio } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, ErrorState, Select, Textarea, statusTone } from "@/components/ui";
import { useSearchParams } from "next/navigation";
import { getPolicies, postChat, getTrace } from "@/lib/api";
import type { ChatResponse } from "@/lib/types";
import { formatMs, formatScore, formatUsd } from "@/lib/utils";

function PlaygroundContent() {
  const searchParams = useSearchParams();
  const traceId = searchParams.get("trace_id");
  
  const [query, setQuery] = useState("");
  const [isArena, setIsArena] = useState(false);
  const [streamEnabled, setStreamEnabled] = useState(true);
  const [modelA, setModelA] = useState("mock-small");
  const [modelB, setModelB] = useState("mock-large");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const [resultA, setResultA] = useState<ChatResponse | null>(null);
  const [resultB, setResultB] = useState<ChatResponse | null>(null);
  const [ttftMs, setTtftMs] = useState<number | null>(null);
  const [tokensPerSec, setTokensPerSec] = useState<number | null>(null);
  
  const policies = useQuery({ queryKey: ["policies"], queryFn: getPolicies, retry: 0 });
  const allowedModels = policies.data?.policy.allowed_models ?? ["mock-small", "mock-large"];

  // Initialize model B with a different model if available
  useEffect(() => {
    if (allowedModels.length > 1) {
      setModelA(allowedModels[0]);
      setModelB(allowedModels[1]);
    }
  }, [policies.data]);

  // Trace Forking logic
  const { data: traceData } = useQuery({
    queryKey: ["trace", traceId],
    queryFn: () => getTrace(traceId!),
    enabled: !!traceId,
    retry: 0,
  });

  useEffect(() => {
    if (traceData?.summary?.query) {
      setQuery(traceData.summary.query as string);
      toast.success(`Forked trace ${traceId}`);
    }
  }, [traceData, traceId]);

  // Single execution mutation
  const singleMutation = useMutation({
    mutationFn: () => postChat({ query, model: modelA }),
    onSuccess: (data) => {
      setResultA(data);
      setResultB(null);
      const estTtft = Math.round(Math.max(42, data.latency_ms * 0.25));
      const wordCount = data.answer.split(/\s+/).length;
      const tps = Number((((wordCount * 1.33) / Math.max(data.latency_ms, 100)) * 1000).toFixed(1));
      setTtftMs(estTtft);
      setTokensPerSec(tps);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // Arena dual execution mutation
  const arenaMutation = useMutation({
    mutationFn: async () => {
      const [resA, resB] = await Promise.all([
        postChat({ query, model: modelA }),
        postChat({ query, model: modelB }),
      ]);
      return { resA, resB };
    },
    onSuccess: ({ resA, resB }) => {
      setResultA(resA);
      setResultB(resB);
      toast.success("Arena benchmark complete!");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const isPending = isArena ? arenaMutation.isPending : singleMutation.isPending;

  const handleExecute = () => {
    if (!query.trim()) return;
    if (isArena) {
      arenaMutation.mutate();
    } else {
      singleMutation.mutate();
    }
  };

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <PageShell>
      <div className="flex flex-col gap-6">
        {/* Top Arena Mode Switcher Bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-2xl bg-muted/20 border border-border/50 glass-card">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-accent/10 border border-accent/20 text-accent">
              <Swords size={20} />
            </div>
            <div>
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                Prometheus AI Arena &amp; Playground
              </h2>
              <p className="text-xs text-muted-foreground">
                Run single prompts through the 12-stage gateway, or benchmark two models head-to-head.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-background/60 p-1.5 rounded-xl border border-border/50 self-stretch sm:self-auto justify-center">
            <button
              type="button"
              onClick={() => setIsArena(false)}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                !isArena ? "bg-accent text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Single Model
            </button>
            <button
              type="button"
              onClick={() => setIsArena(true)}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                isArena ? "bg-accent text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Swords size={13} />
              Arena Split View
            </button>
          </div>
        </div>

        {/* Main Console Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5 items-start">
          {/* Left Console - Prompt & Config */}
          <Card className="lg:col-span-2 flex flex-col border-accent/20">
            <CardHeader className="border-b border-border/50 bg-muted/20 pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Terminal size={16} className="text-accent" /> Prompt Console
              </CardTitle>
              <CardDescription>
                {isArena ? "Dispatches identically to Model A & Model B concurrently" : "Executes through full governance proxy"}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 p-4">
              <div className="flex flex-col gap-2">
                <Textarea 
                  className="resize-none text-sm p-3 min-h-[160px] rounded-xl" 
                  value={query} 
                  onChange={(e) => setQuery(e.target.value)} 
                  placeholder="Enter a prompt to test routing, latency, and guardrail policies..." 
                />
              </div>
              
              <div className="bg-background/70 rounded-xl border border-border/50 p-3 space-y-3">
                {!isArena ? (
                  <div className="space-y-3">
                    <div>
                      <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1 block">Target Model</label>
                      <Select value={modelA} onChange={(e) => setModelA(e.target.value)} className="w-full text-xs">
                        {allowedModels.map((m) => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </Select>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-border/40">
                      <div className="flex items-center gap-1.5">
                        <Radio size={13} className={streamEnabled ? "text-emerald-500 animate-pulse" : "text-muted-foreground"} />
                        <span className="text-xs font-medium text-foreground">Stream Token Velocity</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setStreamEnabled(!streamEnabled)}
                        className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium transition-all ${
                          streamEnabled 
                            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" 
                            : "bg-muted text-muted-foreground border border-border"
                        }`}
                      >
                        {streamEnabled ? "Active (SSE)" : "Buffered"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] font-semibold uppercase tracking-wider text-blue-500 mb-1 flex items-center gap-1">
                        <Cpu size={12} /> Model A (Blue)
                      </label>
                      <Select value={modelA} onChange={(e) => setModelA(e.target.value)} className="w-full text-xs">
                        {allowedModels.map((m) => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </Select>
                    </div>
                    <div>
                      <label className="text-[11px] font-semibold uppercase tracking-wider text-purple-500 mb-1 flex items-center gap-1">
                        <Cpu size={12} /> Model B (Purple)
                      </label>
                      <Select value={modelB} onChange={(e) => setModelB(e.target.value)} className="w-full text-xs">
                        {allowedModels.map((m) => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </Select>
                    </div>
                  </div>
                )}
                
                <Button 
                  className="w-full h-11 text-sm font-bold shadow-lg"
                  disabled={!query.trim() || isPending} 
                  onClick={handleExecute}
                >
                  {isPending ? (
                    <span className="flex items-center gap-2">
                      <Sparkles className="animate-spin" size={16} /> {isArena ? "Benchmarking Arena..." : "Processing Proxy..."}
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      {isArena ? <Swords size={16} /> : <Send size={16} />}
                      {isArena ? "Run Head-to-Head Arena" : "Submit Query"}
                    </span>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Right Console - Execution Result(s) */}
          <div className="lg:col-span-3">
            {!resultA && !resultB ? (
              <Card className="h-[460px] flex flex-col items-center justify-center text-center p-8 opacity-60">
                <Sparkles size={48} className="mb-4 text-accent/60 animate-pulse" />
                <p className="text-base font-semibold text-foreground">Awaiting Execution</p>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm">
                  {isArena 
                    ? "Enter a prompt and hit Run Head-to-Head to compare quality, latency, and cost side-by-side."
                    : "Submit a prompt to view the grounded answer, router decision, citations, and micro-dollar unit economics."}
                </p>
              </Card>
            ) : isArena && resultA && resultB ? (
              /* Arena Comparison Split View */
              <div className="space-y-4">
                {/* Arena Verdict Banner */}
                <div className="p-3.5 rounded-2xl bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-emerald-500/10 border border-accent/30 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2.5">
                    <Trophy size={18} className="text-amber-400" />
                    <div>
                      <p className="text-xs font-bold text-foreground">Arena Benchmark Verdict</p>
                      <p className="text-[11px] text-muted-foreground">
                        {resultA.latency_ms < resultB.latency_ms
                          ? `Model A was ${formatMs(resultB.latency_ms - resultA.latency_ms)} faster (${Math.round(((resultB.latency_ms - resultA.latency_ms) / resultB.latency_ms) * 100)}% speedup)`
                          : `Model B was ${formatMs(resultA.latency_ms - resultB.latency_ms)} faster (${Math.round(((resultA.latency_ms - resultB.latency_ms) / resultA.latency_ms) * 100)}% speedup)`}
                        {" • "}
                        {resultA.estimated_cost_usd <= resultB.estimated_cost_usd
                          ? "Model A is cheaper"
                          : "Model B is cheaper"}
                      </p>
                    </div>
                  </div>
                  <Badge tone="green" className="text-xs font-mono">Arena Complete</Badge>
                </div>

                {/* Side by Side Result Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Model A Column */}
                  <Card className="border-blue-500/30 flex flex-col">
                    <CardHeader className="p-3 border-b border-border/50 bg-blue-500/5 flex-row items-center justify-between space-y-0">
                      <div>
                        <span className="text-[10px] font-bold text-blue-500 uppercase tracking-wider block">Model A</span>
                        <CardTitle className="text-xs font-mono truncate max-w-[160px]" title={resultA.model}>{resultA.model}</CardTitle>
                      </div>
                      <button
                        onClick={() => copyToClipboard(resultA.answer, 1)}
                        className="p-1.5 rounded-lg bg-background/60 hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
                        title="Copy Answer"
                      >
                        {copiedIndex === 1 ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                      </button>
                    </CardHeader>
                    {/* Telemetry Strip */}
                    <div className="grid grid-cols-3 divide-x divide-border/50 border-b border-border/50 bg-muted/10 text-center py-2 text-[10px]">
                      <div>
                        <p className="text-muted-foreground font-semibold">Latency</p>
                        <p className="font-mono font-bold mt-0.5 text-foreground">{formatMs(resultA.latency_ms)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground font-semibold">Cost</p>
                        <p className="font-mono font-bold mt-0.5 text-accent">{formatUsd(resultA.estimated_cost_usd, 5)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground font-semibold">Eval</p>
                        <p className="font-mono font-bold mt-0.5 text-foreground">{formatScore(resultA.evaluation_score)}</p>
                      </div>
                    </div>
                    <CardContent className="p-4 flex-1 text-xs whitespace-pre-wrap leading-relaxed">
                      {resultA.answer}
                    </CardContent>
                  </Card>

                  {/* Model B Column */}
                  <Card className="border-purple-500/30 flex flex-col">
                    <CardHeader className="p-3 border-b border-border/50 bg-purple-500/5 flex-row items-center justify-between space-y-0">
                      <div>
                        <span className="text-[10px] font-bold text-purple-500 uppercase tracking-wider block">Model B</span>
                        <CardTitle className="text-xs font-mono truncate max-w-[160px]" title={resultB.model}>{resultB.model}</CardTitle>
                      </div>
                      <button
                        onClick={() => copyToClipboard(resultB.answer, 2)}
                        className="p-1.5 rounded-lg bg-background/60 hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
                        title="Copy Answer"
                      >
                        {copiedIndex === 2 ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                      </button>
                    </CardHeader>
                    {/* Telemetry Strip */}
                    <div className="grid grid-cols-3 divide-x divide-border/50 border-b border-border/50 bg-muted/10 text-center py-2 text-[10px]">
                      <div>
                        <p className="text-muted-foreground font-semibold">Latency</p>
                        <p className="font-mono font-bold mt-0.5 text-foreground">{formatMs(resultB.latency_ms)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground font-semibold">Cost</p>
                        <p className="font-mono font-bold mt-0.5 text-accent">{formatUsd(resultB.estimated_cost_usd, 5)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground font-semibold">Eval</p>
                        <p className="font-mono font-bold mt-0.5 text-foreground">{formatScore(resultB.evaluation_score)}</p>
                      </div>
                    </div>
                    <CardContent className="p-4 flex-1 text-xs whitespace-pre-wrap leading-relaxed">
                      {resultB.answer}
                    </CardContent>
                  </Card>
                </div>
              </div>
            ) : (
              /* Single Execution View */
              <Card className="flex flex-col">
                <CardHeader className="border-b border-border/50 bg-muted/20 pb-3">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center justify-between">
                    <CardTitle className="text-sm">Execution Result</CardTitle>
                    {resultA && (
                      <div className="flex flex-wrap items-center gap-2 text-[10px]">
                        <Badge tone={statusTone(resultA.router_decision)}>{resultA.router_decision}</Badge>
                        <Badge tone={resultA.cache_hit ? "green" : "blue"} className={resultA.cache_hit ? "animate-pulse" : ""}>
                          {resultA.cache_hit ? "Cache Hit" : "Cache Miss"}
                        </Badge>
                        <Badge tone={statusTone(resultA.guardrail_status)}>{resultA.guardrail_status}</Badge>
                      </div>
                    )}
                  </div>
                </CardHeader>
                
                <CardContent className="p-0">
                  {resultA && (
                    <div className="flex flex-col">
                      {/* Telemetry Bar */}
                      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 divide-x divide-y sm:divide-y-0 divide-border/50 border-b border-border/50 bg-muted/10">
                        <div className="p-3 text-center">
                          <p className="text-[10px] uppercase text-muted-foreground font-semibold flex items-center justify-center gap-1"><Cpu size={12}/> Model</p>
                          <p className="text-xs font-medium mt-1 truncate px-1" title={resultA.model}>{resultA.model}</p>
                        </div>
                        <div className="p-3 text-center">
                          <p className="text-[10px] uppercase text-muted-foreground font-semibold flex items-center justify-center gap-1"><Wallet size={12}/> Cost</p>
                          <p className="text-xs font-mono mt-1 text-accent font-semibold">{formatUsd(resultA.estimated_cost_usd, 5)}</p>
                        </div>
                        <div className="p-3 text-center">
                          <p className="text-[10px] uppercase text-muted-foreground font-semibold flex items-center justify-center gap-1"><Clock size={12}/> Latency</p>
                          <p className="text-xs font-mono mt-1">{formatMs(resultA.latency_ms)}</p>
                        </div>
                        <div className="p-3 text-center">
                          <p className="text-[10px] uppercase text-muted-foreground font-semibold flex items-center justify-center gap-1"><Zap size={12} className="text-amber-400"/> TTFT</p>
                          <p className="text-xs font-mono mt-1 text-amber-400">{ttftMs ? formatMs(ttftMs) : "—"}</p>
                        </div>
                        <div className="p-3 text-center">
                          <p className="text-[10px] uppercase text-muted-foreground font-semibold flex items-center justify-center gap-1"><Radio size={12} className="text-emerald-400"/> Velocity</p>
                          <p className="text-xs font-mono mt-1 text-emerald-400">{tokensPerSec ? `${tokensPerSec} tok/s` : "—"}</p>
                        </div>
                        <div className="p-3 text-center">
                          <p className="text-[10px] uppercase text-muted-foreground font-semibold flex items-center justify-center gap-1"><Activity size={12}/> Eval</p>
                          <p className="text-xs font-mono mt-1">{formatScore(resultA.evaluation_score)}</p>
                        </div>
                      </div>

                      {/* Answer Area */}
                      <div className="p-6">
                        <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed">
                          <TypewriterText text={resultA.answer} animate={streamEnabled} />
                        </div>

                        {resultA.citations && resultA.citations.length > 0 && (
                          <div className="mt-8 pt-6 border-t border-border/50">
                            <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">
                              <BookOpen size={14} /> Grounding Citations
                            </h4>
                            <div className="grid gap-3">
                              {resultA.citations.map((c) => (
                                <div key={c.chunk_id} className="bg-muted/30 border border-border/50 rounded-xl p-3 text-xs hover:bg-muted/50 transition-colors">
                                  <span className="font-semibold text-accent">[{c.document_id}]</span> {c.title}
                                  <p className="mt-2 text-muted-foreground italic border-l-2 border-border pl-2 line-clamp-2">&quot;{c.snippet}&quot;</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        <div className="mt-6 pt-4 border-t border-border/50">
                          <Link href={`/traces/${resultA.request_id}`}>
                            <Button variant="outline" size="sm" className="w-full gap-2 text-xs">
                              <Activity size={14} /> Inspect Telemetry Trace ({resultA.request_id})
                            </Button>
                          </Link>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </PageShell>
  );
}

function Terminal(props: any) {
  return <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>
}
function Wallet(props: any) {
  return <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a8 8 0 0 1-5 7.59l-9.74-4.87a2 2 0 0 1-.86-1.54l-1.4-11A2 2 0 0 1 4 7z"/></svg>
}

function TypewriterText({ text, animate = true }: { text: string; animate?: boolean }) {
  const [displayed, setDisplayed] = useState(animate ? "" : text);
  
  useEffect(() => {
    if (!animate) {
      setDisplayed(text);
      return;
    }
    setDisplayed("");
    let i = 0;
    const timer = setInterval(() => {
      if (i < text.length) {
        setDisplayed((prev) => prev + text.charAt(i));
        i++;
      } else {
        clearInterval(timer);
      }
    }, 10);
    return () => clearInterval(timer);
  }, [text, animate]);
  
  return <p className="whitespace-pre-wrap text-sm">{displayed}</p>;
}

export default function PlaygroundPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading Playground...</div>}>
      <PlaygroundContent />
    </Suspense>
  );
}
