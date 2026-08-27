"use client";
import { useQuery } from "@tanstack/react-query";
import { getApiMode, getBudget } from "@/lib/api";
import { Sidebar, Topbar } from "@/components/layout";
import { Skeleton } from "@/components/ui";
import { useEventStream } from "@/lib/sse";

export function PageShell({ children }: { children: React.ReactNode }) {
  const mode = useQuery({ queryKey: ["api-mode"], queryFn: getApiMode, staleTime: 30_000, refetchInterval: 30_000 });
  const budget = useQuery({ queryKey: ["budget"], queryFn: getBudget, refetchInterval: 30_000, retry: 0 });
  useEventStream(mode.data === "live");

  return (
    <div className="min-h-screen lg:pl-60">
      <Sidebar />
      {mode.isLoading ? (
        <div className="p-6"><Skeleton className="h-10 w-full" /></div>
      ) : (
        <Topbar mode={mode.data ?? "loading"} killSwitch={budget.data?.kill_switch_mode} />
      )}
      <main className="p-6">{children}</main>
    </div>
  );
}
