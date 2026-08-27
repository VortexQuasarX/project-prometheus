"use client";
// Single shared SSE subscription: invalidates TanStack Query caches as live
// events arrive from the backend outbox (request_started, agent_*,
// budget_warning, action_*). Falls back to polling-friendly invalidation only.
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export function useEventStream(enabled: boolean) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled) return;
    let source: EventSource | null = null;
    let backoff = 1000;
    let stopped = false;

    const connect = () => {
      if (stopped) return;
      source = new EventSource(`${API_BASE}/events/stream`);
      source.onmessage = (message) => {
        backoff = 1000;
        try {
          const parsed = JSON.parse(message.data) as { event?: string };
          const event = parsed.event ?? "";
          if (event === "action_pending_approval") {
            void queryClient.invalidateQueries({ queryKey: ["pending-actions"] });
          } else if (event === "action_approved" || event === "action_applied") {
            void queryClient.invalidateQueries({ queryKey: ["pending-actions"] });
            void queryClient.invalidateQueries({ queryKey: ["agent-runs"] });
            void queryClient.invalidateQueries({ queryKey: ["budget"] });
          } else if (event === "budget_warning") {
            void queryClient.invalidateQueries({ queryKey: ["budget"] });
            toast.warning("Budget warning");
          } else if (event.startsWith("agent_")) {
            void queryClient.invalidateQueries({ queryKey: ["agent-runs"] });
          }
        } catch {
          /* tolerate malformed frames */
        }
      };
      source.onerror = () => {
        source?.close();
        if (!stopped) {
          setTimeout(connect, Math.min(backoff, 30000));
          backoff = Math.min(backoff * 2, 30000);
        }
      };
    };

    connect();
    return () => {
      stopped = true;
      source?.close();
    };
  }, [enabled, queryClient]);
}
