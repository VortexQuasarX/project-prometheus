"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState, useEffect, Suspense } from "react";
import { toast } from "sonner";
import { Send, Sparkles, BookOpen, Clock, Activity, Cpu } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, ErrorState, Select, Textarea, statusTone, AnimatedCounter } from "@/components/ui";
import { useSearchParams } from "next/navigation";
import { getPolicies, postChat, getTrace } from "@/lib/api";
import type { ChatResponse } from "@/lib/types";
import { formatMs, formatScore, formatUsd } from "@/lib/utils";

function PlaygroundContent() {
  const searchParams = useSearchParams();
  const traceId = searchParams.get("trace_id");
  
  const [query, setQuery] = useState("");
  const [model, setModel] = useState("mock-small");
  const [result, setResult] = useState<ChatResponse | null>(null);
  const policies = useQuery({ queryKey: ["policies"], queryFn: getPolicies, retry: 0 });

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

  const mutation = useMutation({
    mutationFn: () => postChat({ query, model }),
    onSuccess: (data) => setResult(data),
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <PageShell>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5 h-[calc(100vh-8rem)]">
        
        {/* Left Pane - Input */}
        <Card className="lg:col-span-2 flex flex-col h-full border-accent/20">
          <CardHeader className="border-b border-border/50 bg-muted/20">
            <CardTitle className="flex items-center gap-2">
              <Terminal size={18} className="text-accent" /> Prompt Console
            </CardTitle>
            <CardDescription>Executes through the 12-stage governance pipeline</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col gap-4 p-5">
            <div className="flex flex-col flex-1 gap-2">
              <Textarea 
                className="flex-1 resize-none text-base p-4 min-h-[200px]" 
                value={query} 
                onChange={(e) => setQuery(e.target.value)} 
                placeholder="Ask about AI cost governance, FinOps for AI, Bedrock cost controls..." 
              />
            </div>
            
            <div className="bg-background rounded-xl border border-border/50 p-4 space-y-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">Target Model</label>
                <Select value={model} onChange={(e) => setModel(e.target.value)} className="w-full">
                  {(policies.data?.policy.allowed_models ?? ["mock-small", "mock-large"]).map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </Select>
              </div>
              
              <Button 
                className="w-full h-12 text-base font-bold shadow-lg"
                disabled={!query.trim() || mutation.isPending} 
                onClick={() => mutation.mutate()}
              >
                {mutation.isPending ? (
                  <span className="flex items-center gap-2">
                    <Sparkles className="animate-spin" size={18} /> Processing...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Send size={18} /> Submit Query
                  </span>
                )}
              </Button>
            </div>
            
            {mutation.isError ? <ErrorState message={(mutation.error as Error).message} /> : null}
          </CardContent>
        </Card>

        {/* Right Pane - Output */}
        <Card className="lg:col-span-3 flex flex-col h-full">
          <CardHeader className="border-b border-border/50 bg-muted/20">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center justify-between">
              <CardTitle>Execution Result</CardTitle>
              {result ? (
                <div className="flex flex-wrap items-center gap-2 text-[10px]">
                  <Badge tone={statusTone(result.router_decision)}>{result.router_decision}</Badge>
                  <Badge tone={result.cache_hit ? "green" : "blue"} className={result.cache_hit ? "animate-pulse" : ""}>
                    {result.cache_hit ? "Cache Hit" : "Cache Miss"}
                  </Badge>
                  <Badge tone={statusTone(result.guardrail_status)}>{result.guardrail_status}</Badge>
                </div>
              ) : null}
            </div>
          </CardHeader>
          
          <CardContent className="flex-1 overflow-y-auto p-0">
            {!result ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-50">
                <Sparkles size={48} className="mb-4 text-muted-foreground" />
                <p className="text-lg font-medium text-foreground">Awaiting Execution</p>
                <p className="text-sm text-muted-foreground mt-2 max-w-sm">Submit a query to see the grounded answer, router decision, citations, and micro-dollar unit economics.</p>
              </div>
            ) : (
              <div className="flex flex-col h-full">
                {/* Telemetry Bar */}
                <div className="grid grid-cols-4 divide-x divide-border/50 border-b border-border/50 bg-muted/10">
                  <div className="p-3 text-center">
                    <p className="text-[10px] uppercase text-muted-foreground font-semibold flex items-center justify-center gap-1"><Cpu size={12}/> Model</p>
                    <p className="text-xs font-medium mt-1 truncate px-1" title={result.model}>{result.model}</p>
                  </div>
                  <div className="p-3 text-center">
                    <p className="text-[10px] uppercase text-muted-foreground font-semibold flex items-center justify-center gap-1"><Wallet size={12}/> Cost</p>
                    <p className="text-xs font-mono mt-1 text-accent font-semibold">{formatUsd(result.estimated_cost_usd, 5)}</p>
                  </div>
                  <div className="p-3 text-center">
                    <p className="text-[10px] uppercase text-muted-foreground font-semibold flex items-center justify-center gap-1"><Clock size={12}/> Latency</p>
                    <p className="text-xs font-mono mt-1">{formatMs(result.latency_ms)}</p>
                  </div>
                  <div className="p-3 text-center">
                    <p className="text-[10px] uppercase text-muted-foreground font-semibold flex items-center justify-center gap-1"><Activity size={12}/> Eval</p>
                    <p className="text-xs font-mono mt-1">{formatScore(result.evaluation_score)}</p>
                  </div>
                </div>

                {/* Answer Area */}
                <div className="p-6 flex-1 overflow-y-auto">
                  <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed">
                    <TypewriterText text={result.answer} />
                  </div>

                  {result.citations.length > 0 ? (
                    <div className="mt-8 pt-6 border-t border-border/50">
                      <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground mb-4">
                        <BookOpen size={14} /> Grounding Citations
                      </h4>
                      <div className="grid gap-3">
                        {result.citations.map((c) => (
                          <div key={c.chunk_id} className="bg-muted/30 border border-border/50 rounded-xl p-3 text-xs hover:bg-muted/50 transition-colors">
                            <span className="font-semibold text-accent">[{c.document_id}]</span> {c.title}
                            <p className="mt-2 text-muted-foreground italic border-l-2 border-border pl-2 line-clamp-2">&quot;{c.snippet}&quot;</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  
                  <div className="mt-8 pt-4">
                    <Link href={`/traces/${result.request_id}`}>
                      <Button variant="outline" size="sm" className="w-full gap-2">
                        <Activity size={14} /> Analyze Trace {result.request_id}
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PageShell>
  );
}

// Need Terminal icon for local use
function Terminal(props: any) {
  return <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>
}
function Wallet(props: any) {
  return <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a8 8 0 0 1-5 7.59l-9.74-4.87a2 2 0 0 1-.86-1.54l-1.4-11A2 2 0 0 1 4 7z"/></svg>
}

function TypewriterText({ text }: { text: string }) {
  const [displayed, setDisplayed] = useState("");
  
  useEffect(() => {
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
  }, [text]);
  
  return <p className="whitespace-pre-wrap text-sm">{displayed}</p>;
}

export default function PlaygroundPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading Playground...</div>}>
      <PlaygroundContent />
    </Suspense>
  );
}
