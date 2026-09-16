"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Server, KeyRound, RotateCcw, Info, Terminal } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, Input, Label, Skeleton } from "@/components/ui";
import { getApiKey, getHealth, resetDemo, setApiKey } from "@/lib/api";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const health = useQuery({ queryKey: ["health"], queryFn: getHealth, refetchInterval: 30_000, retry: 0 });
  const [key, setKey] = useState("");

  useEffect(() => {
    setKey(getApiKey());
  }, []);

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
      <div className="max-w-5xl">
        <h1 className="text-2xl font-bold tracking-tight mb-6">System Configuration</h1>
        
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 items-start">
          <div className="space-y-6">
            <Card>
              <CardHeader className="border-b border-border/50 bg-muted/10">
                <CardTitle className="flex items-center gap-2"><Server size={18} className="text-accent" /> Backend Gateway</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-6 bg-background rounded-lg border border-border/50 p-4">
                  <div className="flex flex-col">
                    <span className="text-xs uppercase font-bold tracking-wider text-muted-foreground mb-1">Status</span>
                    {health.isLoading ? (
                      <Skeleton className="h-6 w-24" />
                    ) : health.isError ? (
                      <div className="flex items-center gap-2"><div className="h-2.5 w-2.5 rounded-full bg-red-500 animate-pulse"/><span className="font-semibold text-red-500">Offline</span></div>
                    ) : (
                      <div className="flex items-center gap-2"><div className="h-2.5 w-2.5 rounded-full bg-emerald-500"/><span className="font-semibold text-emerald-500">Healthy</span></div>
                    )}
                  </div>
                  
                  {health.isSuccess && (
                    <>
                      <div className="w-px h-10 bg-border/50 mx-4" />
                      <div className="flex flex-col">
                        <span className="text-xs uppercase font-bold tracking-wider text-muted-foreground mb-1">Version</span>
                        <span className="font-mono text-sm font-medium">{health.data.version}</span>
                      </div>
                      <div className="w-px h-10 bg-border/50 mx-4" />
                      <div className="flex flex-col">
                        <span className="text-xs uppercase font-bold tracking-wider text-muted-foreground mb-1">Database</span>
                        <span className="font-mono text-sm font-medium">{health.data.db}</span>
                      </div>
                    </>
                  )}
                </div>

                {health.isError && (
                  <div className="mt-4 p-4 rounded-lg bg-amber-500/10 border border-amber-500/20 text-sm">
                    <p className="font-semibold text-amber-500 mb-2">Connection Refused</p>
                    <p className="text-muted-foreground mb-3">The frontend cannot reach the FastAPI backend.</p>
                    <div className="flex items-center gap-2 bg-background p-2 rounded border border-border">
                      <Terminal size={14} className="text-muted-foreground" />
                      <code className="text-xs font-mono">make api</code>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="border-b border-border/50 bg-muted/10">
                <CardTitle className="flex items-center gap-2"><KeyRound size={18} className="text-accent" /> Identity & Access</CardTitle>
                <CardDescription>X-API-Key injected into all backend requests</CardDescription>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div>
                  <Label className="mb-2 block">Bearer Token</Label>
                  <div className="relative">
                    <Input 
                      type="password" 
                      value={key} 
                      onChange={(e) => setKey(e.target.value)} 
                      placeholder="e.g. prometheus-admin" 
                      className="pr-20"
                    />
                    <div className="absolute right-1 top-1 flex gap-1">
                      <Button size="sm" variant="ghost" className="h-8 px-2 text-[10px]" onClick={() => { setKey(""); setApiKey(""); toast.success("Cleared"); }}>Clear</Button>
                      <Button size="sm" className="h-8 px-3 text-[10px]" onClick={() => { 
                        setApiKey(key); 
                        toast.success("API Key Saved"); 
                        void queryClient.invalidateQueries(); 
                      }}>Save</Button>
                    </div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Keys are stored in your browser&apos;s <code className="text-[10px] bg-muted px-1 rounded">localStorage</code> and never sent to our servers for analytics. Use <code className="text-[10px] font-bold text-foreground">prometheus-admin</code> for full read/write access.
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="border-amber-500/30">
              <CardHeader className="border-b border-amber-500/10 bg-amber-500/5">
                <CardTitle className="flex items-center gap-2 text-amber-500"><RotateCcw size={18} /> Demo Environment Reset</CardTitle>
                <CardDescription>Destroy and reseed all operational data</CardDescription>
              </CardHeader>
              <CardContent className="p-6">
                <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
                  This will wipe all telemetry, traces, audit logs, cached responses, and agent runs, then reseed the database with the &quot;Recruiter Demo&quot; baseline (5 RAG documents, base policies).
                </p>
                <Button variant="outline" className="w-full gap-2 border-amber-500/30 hover:bg-amber-500/10 hover:text-amber-500" disabled={reset.isPending} onClick={() => reset.mutate()}>
                  <RotateCcw size={16} className={reset.isPending ? "animate-spin" : ""} /> {reset.isPending ? "Reseeding Database..." : "Factory Reset"}
                </Button>
              </CardContent>
            </Card>

            <Card className="bg-transparent border-dashed">
              <CardContent className="p-6 flex flex-col items-center justify-center text-center opacity-70">
                <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center mb-4">
                  <Info size={24} className="text-muted-foreground" />
                </div>
                <h3 className="font-bold mb-2">Project Prometheus v1.0</h3>
                <p className="text-xs text-muted-foreground">The premier AI Gateway for autonomous FinOps, guardrails, and enterprise policy enforcement.</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </PageShell>
  );
}
