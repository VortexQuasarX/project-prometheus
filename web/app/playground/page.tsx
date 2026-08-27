"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { PageShell } from "@/components/page-shell";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, CardDescription, ErrorState, Select, Textarea, statusTone } from "@/components/ui";
import { getPolicies, postChat } from "@/lib/api";
import type { ChatResponse } from "@/lib/types";
import { formatMs, formatScore, formatUsd } from "@/lib/utils";

export default function PlaygroundPage() {
  const [query, setQuery] = useState("");
  const [model, setModel] = useState("mock-small");
  const [result, setResult] = useState<ChatResponse | null>(null);
  const policies = useQuery({ queryKey: ["policies"], queryFn: getPolicies, retry: 0 });

  const mutation = useMutation({
    mutationFn: () => postChat({ query, model }),
    onSuccess: (data) => setResult(data),
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <PageShell>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Query</CardTitle>
            <CardDescription>Runs the full gateway pipeline: guardrails → router → cache → RAG → LLM</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea rows={5} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask about AI cost governance, FinOps for AI, Bedrock cost controls..." />
            <div className="flex items-center gap-2">
              <Select value={model} onChange={(e) => setModel(e.target.value)}>
                {(policies.data?.policy.allowed_models ?? ["mock-small", "mock-large"]).map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </Select>
              <Button disabled={!query.trim() || mutation.isPending} onClick={() => mutation.mutate()}>
                {mutation.isPending ? "Running..." : "Send"}
              </Button>
            </div>
            {mutation.isError ? <ErrorState message={(mutation.error as Error).message} /> : null}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Response</CardTitle>
            {result ? (
              <div className="flex flex-wrap items-center gap-1.5">
                <Badge tone={statusTone(result.router_decision)}>{result.router_decision}</Badge>
                <Badge tone={result.cache_hit ? "green" : "blue"}>{result.cache_hit ? "cache hit" : "cache miss"}</Badge>
                <Badge tone={statusTone(result.guardrail_status)}>{result.guardrail_status}</Badge>
                <Badge tone="gray">{result.provider} / {result.model}</Badge>
                <Badge tone="gray">{formatUsd(result.estimated_cost_usd)}</Badge>
                <Badge tone="gray">{formatMs(result.latency_ms)}</Badge>
                <Badge tone="gray">eval {formatScore(result.evaluation_score)}</Badge>
              </div>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-3">
            {!result ? (
              <p className="text-sm text-muted-foreground">Send a query to see the grounded answer, router decision, citations and unit economics.</p>
            ) : (
              <>
                <p className="whitespace-pre-wrap text-sm">{result.answer}</p>
                {result.citations.length > 0 ? (
                  <div>
                    <p className="mb-1 text-xs font-semibold text-muted-foreground">Citations</p>
                    <ul className="space-y-1 text-xs text-muted-foreground">
                      {result.citations.map((c) => (
                        <li key={c.chunk_id}>[{c.document_id}] {c.title} · {c.chunk_id} — {c.snippet}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <p className="text-xs">
                  <Link className="text-accent hover:underline" href={`/traces/${result.request_id}`}>Open trace {result.request_id}</Link>
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </PageShell>
  );
}
