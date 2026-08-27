"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
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
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Connection</CardTitle>
            <CardDescription>Backend liveness and identity</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {health.isLoading ? (
              <Skeleton className="h-8" />
            ) : health.isError ? (
              <p className="flex items-center gap-2">
                <Badge tone="red">offline</Badge> Start the API: <code className="rounded bg-muted px-1">make api</code>
              </p>
            ) : (
              <p className="flex items-center gap-2">
                <Badge tone="green">healthy</Badge> v{health.data?.version} Â· db {health.data?.db}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              The UI calls the API through a same-origin rewrite of <code className="rounded bg-muted px-1">/api/v1</code>, so no CORS setup is needed locally.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>API key</CardTitle>
            <CardDescription>Sent as X-API-Key on every request. Seeded demo keys: admin and viewer (printed by the seed script).</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Label className="text-xs">X-API-Key</Label>
            <Input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder="paste the seeded demo key" />
            <div className="flex gap-2">
              <Button size="sm" onClick={() => { setApiKey(key); toast.success("API key saved locally"); }}>Save</Button>
              <Button size="sm" variant="outline" onClick={() => { setKey(""); setApiKey(""); toast.success("API key cleared"); }}>Clear</Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Demo data</CardTitle>
            <CardDescription>Reset the database to the recruiter-demo state (documents, usage history, pending approval, eval run)</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="destructive" disabled={reset.isPending} onClick={() => reset.mutate()}>
              {reset.isPending ? "Resetting..." : "Reset demo data"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>About</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Project Prometheus â€” an agentic AI gateway that routes, caches, retrieves, evaluates, governs, observes and optimizes LLM usage while generating auditable cost-saving actions.
          </CardContent>
        </Card>
      </div>
    </PageShell>
  );
}
