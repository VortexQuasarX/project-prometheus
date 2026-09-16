import { motion } from "framer-motion";
"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Activity, Search, ServerCrash } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, ErrorState, Skeleton, Table, Td, Th, statusTone } from "@/components/ui";
import { getTraces } from "@/lib/api";
import { formatMs, formatTime, formatUsd } from "@/lib/utils";

import { useState, useMemo } from "react";

export default function TracesPage() {
  const traces = useQuery({ queryKey: ["traces"], queryFn: () => getTraces(100), refetchInterval: 15_000, retry: 0 });
  const [searchTerm, setSearchTerm] = useState("");
  const [filterMode, setFilterMode] = useState<"all" | "success" | "cache_hit" | "slow" | "error">("all");

  const filteredItems = useMemo(() => {
    const raw = traces.data?.items ?? [];
    return raw.filter((t) => {
      // Search term matching
      const matchesSearch =
        !searchTerm.trim() ||
        t.request_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (t.model && t.model.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (t.router_decision && t.router_decision.toLowerCase().includes(searchTerm.toLowerCase()));

      if (!matchesSearch) return false;

      // Status pill filter
      if (filterMode === "success") return t.status === "success" || t.status === "200";
      if (filterMode === "cache_hit") return t.cache_hit === true;
      if (filterMode === "slow") return t.latency_ms > 1000;
      if (filterMode === "error") return t.status === "error" || t.status === "blocked" || (t.status && t.status.startsWith("5"));

      return true;
    });
  }, [traces.data?.items, searchTerm, filterMode]);

  return (
    <PageShell>
      <Card>
        <CardHeader className="flex-col sm:flex-row items-start sm:items-end justify-between space-y-3 sm:space-y-0 border-b border-border/50 bg-muted/10 pb-4 gap-4">
          <div>
            <div className="flex items-center gap-3">
              <CardTitle className="flex items-center gap-2"><Activity size={20} className="text-accent" /> Telemetry Traces</CardTitle>
              <Badge tone="gray" className="text-[10px] font-mono">
                {filteredItems.length} of {traces.data?.items?.length ?? 0}
              </Badge>
            </div>
            <CardDescription className="mt-1">Distributed tracing and routing telemetry for every AI invocation</CardDescription>
          </div>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
            <div className="flex items-center gap-1 bg-background/50 border border-border/50 p-1 rounded-xl text-xs">
              <button
                onClick={() => setFilterMode("all")}
                className={`px-2.5 py-1 rounded-lg font-medium transition-all ${filterMode === "all" ? "bg-accent text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                All
              </button>
              <button
                onClick={() => setFilterMode("cache_hit")}
                className={`px-2.5 py-1 rounded-lg font-medium transition-all ${filterMode === "cache_hit" ? "bg-emerald-600 text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                Cache Hits
              </button>
              <button
                onClick={() => setFilterMode("slow")}
                className={`px-2.5 py-1 rounded-lg font-medium transition-all ${filterMode === "slow" ? "bg-amber-600 text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                &gt;1s Slow
              </button>
              <button
                onClick={() => setFilterMode("error")}
                className={`px-2.5 py-1 rounded-lg font-medium transition-all ${filterMode === "error" ? "bg-red-600 text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                Errors/Blocked
              </button>
            </div>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input 
                type="text" 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search ID, model, decision..." 
                className="h-9 w-full sm:w-56 rounded-xl border border-border/50 bg-background/50 pl-9 pr-3 text-xs outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {traces.isLoading ? (
             <div className="p-6 space-y-4">
               {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12" />)}
             </div>
          ) : traces.isError ? (
            <div className="p-6"><ErrorState message={(traces.error as Error).message} /></div>
          ) : filteredItems.length === 0 ? (
            <EmptyState title="No matching traces found" hint="Try clearing the search or changing the filter pills above." icon={<ServerCrash size={32} />} />
          ) : (
              <Table>
                <thead>
                  <tr>
                    <Th>Request ID</Th>
                    <Th>Time</Th>
                    <Th>Status</Th>
                    <Th>Router Decision</Th>
                    <Th>Target Model</Th>
                    <Th>Cache</Th>
                    <Th className="text-right">Latency</Th>
                    <Th className="text-right">Cost</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {filteredItems.map((t) => (
                    <tr key={t.request_id} className="hover:bg-white/5 transition-colors group">
                      <Td>
                        <Link className="font-mono text-xs font-semibold text-accent group-hover:underline flex items-center gap-1" href={`/traces/${t.request_id}`}>
                          {t.request_id.split('-')[0]}...{t.request_id.split('-').pop()}
                        </Link>
                      </Td>
                      <Td className="text-[11px] text-muted-foreground">{formatTime(t.created_at)}</Td>
                      <Td><Badge tone={statusTone(t.status)}>{t.status}</Badge></Td>
                      <Td><Badge tone={statusTone(t.router_decision)}>{t.router_decision ?? "—"}</Badge></Td>
                      <Td>
                        <span className="block text-xs max-w-[150px] truncate" title={t.model ?? ""}>{t.model ?? "—"}</span>
                      </Td>
                      <Td>
                        <Badge tone={t.cache_hit ? "green" : "gray"} className={t.cache_hit ? "animate-pulse drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]" : ""}>
                          {t.cache_hit ? "hit" : "miss"}
                        </Badge>
                      </Td>
                      <Td className="tabular text-right text-xs">
                        {t.latency_ms > 2000 ? (
                          <span className="text-red-500 font-medium drop-shadow-[0_0_5px_rgba(239,68,68,0.5)]">{formatMs(t.latency_ms)}</span>
                        ) : t.latency_ms > 1000 ? (
                          <span className="text-amber-500 font-medium">{formatMs(t.latency_ms)}</span>
                        ) : (
                          formatMs(t.latency_ms)
                        )}
                      </Td>
                      <Td className="tabular text-right text-xs font-medium">
                        {t.cost_usd === 0 ? (
                          <span className="text-muted-foreground">free</span>
                        ) : (
                          <span className="text-emerald-500">{formatUsd(t.cost_usd, 5)}</span>
                        )}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
          )}
        </CardContent>
      </Card>
    </PageShell>
  );
}
