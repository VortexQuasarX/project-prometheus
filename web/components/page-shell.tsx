"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { getApiMode, getBudget } from "@/lib/api";
import { Sidebar, Topbar } from "@/components/layout";
import { Skeleton } from "@/components/ui";
import { useEventStream } from "@/lib/sse";

export function PageShell({ children }: { children: React.ReactNode }) {
  const mode = useQuery({ queryKey: ["api-mode"], queryFn: getApiMode, staleTime: 30_000, refetchInterval: 30_000 });
  const budget = useQuery({ queryKey: ["budget"], queryFn: getBudget, refetchInterval: 30_000, retry: 0 });
  useEventStream(mode.data === "live");
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen lg:pl-64">
      <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
      {mode.isLoading ? (
        <div className="p-6"><Skeleton className="h-16 w-full" /></div>
      ) : (
        <Topbar mode={mode.data ?? "loading"} killSwitch={budget.data?.kill_switch_mode} setMobileOpen={setMobileOpen} />
      )}
      <main className="p-6 md:p-8 max-w-7xl mx-auto">{children}</main>
    </div>
  );
}
