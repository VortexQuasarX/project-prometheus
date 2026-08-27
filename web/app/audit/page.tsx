"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { PageShell } from "@/components/page-shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, EmptyState, ErrorState, Input, Skeleton, Table, Td, Th } from "@/components/ui";
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
      <Card>
        <CardHeader className="flex-row items-end justify-between space-y-0">
          <div>
            <CardTitle>Audit trail</CardTitle>
            <CardDescription>Append-only and immutable — every governance action is recorded</CardDescription>
          </div>
          <div className="flex gap-2">
            <Input placeholder="filter actor" value={actor} onChange={(e) => setActor(e.target.value)} className="w-40" />
            <Input placeholder="filter action" value={action} onChange={(e) => setAction(e.target.value)} className="w-40" />
          </div>
        </CardHeader>
        <CardContent>
          {audit.isLoading ? (
            <Skeleton className="h-64" />
          ) : audit.isError ? (
            <ErrorState message={(audit.error as Error).message} />
          ) : items.length === 0 ? (
            <EmptyState title="No audit events match" hint="Clear the filters or run some governance actions." />
          ) : (
            <Table>
              <thead>
                <tr><Th>Event</Th><Th>Actor</Th><Th>Role</Th><Th>Action</Th><Th>Resource</Th><Th>Time</Th></tr>
              </thead>
              <tbody>
                {items.map((e) => (
                  <tr key={e.event_id} className="border-t border-border align-top">
                    <Td className="font-mono text-xs">{e.event_id}</Td>
                    <Td className="text-xs">{e.actor}</Td>
                    <Td className="text-xs">{e.role}</Td>
                    <Td><span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{e.action}</span></Td>
                    <Td className="text-xs">{e.resource}</Td>
                    <Td className="text-xs text-muted-foreground">{formatTime(e.created_at)}</Td>
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
