"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Search, Database, ListFilter } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, ErrorState, Input, Skeleton } from "@/components/ui";
import { getAudit } from "@/lib/api";
import { formatTime } from "@/lib/utils";

export default function AuditPage() {
  const audit = useQuery({ queryKey: ["audit"], queryFn: () => getAudit(200), refetchInterval: 30_000, retry: 0 });
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");

  const items = (audit.data?.items ?? []).filter(
    (e) =>
      (actor === "" || e.actor.toLowerCase().includes(actor.toLowerCase())) &&
      (action === "" || e.action.toLowerCase().includes(action.toLowerCase())),
  );

  return (
    <PageShell>
      <Card className="flex flex-col h-[calc(100vh-8rem)]">
        <CardHeader className="border-b border-border/50 bg-muted/10 pb-4 shrink-0">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2"><Database size={20} className="text-accent" /> Governance Ledger</CardTitle>
              <CardDescription className="mt-1">Cryptographically immutable audit trail</CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input 
                  placeholder="Actor (e.g. system)" 
                  value={actor} 
                  onChange={(e) => setActor(e.target.value)} 
                  className="h-9 w-40 rounded-lg border border-border/50 bg-background/50 pl-9 pr-3 text-xs outline-none focus:border-accent focus:ring-1 transition-all" 
                />
              </div>
              <div className="relative">
                <ListFilter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input 
                  placeholder="Action (e.g. policy)" 
                  value={action} 
                  onChange={(e) => setAction(e.target.value)} 
                  className="h-9 w-40 rounded-lg border border-border/50 bg-background/50 pl-9 pr-3 text-xs outline-none focus:border-accent focus:ring-1 transition-all" 
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0 flex-1 overflow-hidden flex flex-col">
          {audit.isLoading ? (
            <div className="p-6 space-y-4">
              {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-16" />)}
            </div>
          ) : audit.isError ? (
            <div className="p-6"><ErrorState message={(audit.error as Error).message} /></div>
          ) : items.length === 0 ? (
            <div className="p-6"><EmptyState title="No events found" hint="Try clearing your filters." /></div>
          ) : (
            <div className="overflow-y-auto flex-1 p-6">
              <div className="relative border-l border-border/50 ml-4 space-y-6 pb-6">
                {items.map((e) => (
                  <div key={e.event_id} className="relative pl-6 group">
                    <div className="absolute w-3 h-3 bg-muted border-2 border-background rounded-full -left-[6.5px] top-1.5 group-hover:bg-accent group-hover:border-accent/20 transition-colors" />
                    
                    <div className="bg-background/40 hover:bg-muted/20 border border-border/40 rounded-xl p-4 transition-colors">
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-foreground bg-muted px-2 py-0.5 rounded">{e.action}</span>
                          <span className="text-xs text-muted-foreground">on</span>
                          <span className="text-xs font-medium text-accent">{e.resource}</span>
                        </div>
                        <span className="text-[11px] text-muted-foreground font-mono">{formatTime(e.created_at)}</span>
                      </div>
                      
                      <div className="flex items-center gap-4 text-xs mt-3">
                        <div className="flex items-center gap-1.5">
                          <span className="text-muted-foreground uppercase text-[9px] font-bold tracking-wider">Actor</span>
                          <span className="font-medium">{e.actor}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-muted-foreground uppercase text-[9px] font-bold tracking-wider">Role</span>
                          <span className="font-mono bg-muted/50 px-1.5 rounded text-[10px]">{e.role}</span>
                        </div>
                        <div className="flex items-center gap-1.5 ml-auto">
                          <span className="text-muted-foreground font-mono text-[9px]">{e.event_id}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </PageShell>
  );
}
