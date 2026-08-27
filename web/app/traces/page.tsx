"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { PageShell } from "@/components/page-shell";
import { Badge, EmptyState, ErrorState, Skeleton, Table, Td, Th, statusTone } from "@/components/ui";
import { getTraces } from "@/lib/api";
import { formatMs, formatTime, formatUsd } from "@/lib/utils";

export default function TracesPage() {
  const traces = useQuery({ queryKey: ["traces"], queryFn: () => getTraces(100), refetchInterval: 15_000, retry: 0 });

  return (
    <PageShell>
      {traces.isLoading ? (
        <Skeleton className="h-64" />
      ) : traces.isError ? (
        <ErrorState message={(traces.error as Error).message} />
      ) : (traces.data?.items ?? []).length === 0 ? (
        <EmptyState title="No traces yet" hint="Send a playground query first." />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Request</Th><Th>Model</Th><Th>Router</Th><Th>Cache</Th><Th>Status</Th><Th className="text-right">Latency</Th><Th className="text-right">Cost</Th><Th>Time</Th>
            </tr>
          </thead>
          <tbody>
            {(traces.data?.items ?? []).map((t) => (
              <tr key={t.request_id} className="border-t border-border hover:bg-muted/40">
                <Td><Link className="font-mono text-xs text-accent hover:underline" href={`/traces/${t.request_id}`}>{t.request_id}</Link></Td>
                <Td className="text-xs">{t.model ?? "—"}</Td>
                <Td><Badge tone={statusTone(t.router_decision)}>{t.router_decision ?? "—"}</Badge></Td>
                <Td><Badge tone={t.cache_hit ? "green" : "gray"}>{t.cache_hit ? "hit" : "miss"}</Badge></Td>
                <Td><Badge tone={statusTone(t.status)}>{t.status}</Badge></Td>
                <Td className="tabular text-right">{formatMs(t.latency_ms)}</Td>
                <Td className="tabular text-right">{formatUsd(t.cost_usd)}</Td>
                <Td className="text-xs text-muted-foreground">{formatTime(t.created_at)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </PageShell>
  );
}
