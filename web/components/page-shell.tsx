"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { motion } from "framer-motion";
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
    <div className="min-h-screen lg:pl-64 flex flex-col">
      <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
      {mode.isLoading ? (
        <div className="p-6 border-b border-border/50 bg-background/50 backdrop-blur-xl sticky top-0 z-40"><Skeleton className="h-10 w-full" /></div>
      ) : (
        <Topbar mode={mode.data ?? "loading"} killSwitch={budget.data?.kill_switch_mode} setMobileOpen={setMobileOpen} />
      )}
      <motion.main 
        initial={{ opacity: 0, y: 15, filter: 'blur(10px)' }} 
        animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} 
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="p-4 md:p-6 lg:p-8 w-full max-w-7xl mx-auto flex-1"
      >
        {children}
      </motion.main>
    </div>
  );
}
