"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Activity, Search, ServerCrash } from "lucide-react";
import { PageShell } from "@/components/page-shell";
import { Badge, Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, ErrorState, Skeleton, Table, Td, Th, statusTone } from "@/components/ui";
import { getTraces } from "@/lib/api";
import { formatMs, formatTime, formatUsd } from "@/lib/utils";

export default function TracesPage() {
  const traces = useQuery({ queryKey: ["traces"], queryFn: () => getTraces(100), refetchInterval: 15_000, retry: 0 });

  return (
    <PageShell>
      <Card>
        <CardHeader className="flex-row items-end justify-between space-y-0 border-b border-border/50 bg-muted/10 pb-4">
          <div>
            <CardTitle className="flex items-center gap-2"><Activity size={20} className="text-accent" /> Telemetry Traces</CardTitle>
            <CardDescription className="mt-1">Distributed tracing for every AI invocation</CardDescription>
          </div>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input 
              type="text" 
              placeholder="Filter by request ID..." 
              className="h-9 w-64 rounded-lg border border-border/50 bg-background/50 pl-9 pr-3 text-xs outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
              disabled
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {traces.isLoading ? (
             <div className="p-6 space-y-4">
               {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12" />)}
             </div>
          ) : traces.isError ? (
            <div className="p-6"><ErrorState message={(traces.error as Error).message} /></div>
          ) : (traces.data?.items ?? []).length === 0 ? (
            <EmptyState title="No telemetry data" hint="Execute queries in the playground to generate traces." icon={<ServerCrash size={32} />} />
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
                  {(traces.data?.items ?? []).map((t) => (
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
