"use client";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { useState, useEffect } from "react";
import { Activity, Bot, Gauge, LayoutDashboard, ScrollText, Settings, ShieldCheck, Terminal, Menu, X, Moon, Sun } from "lucide-react";
import { Badge, Button } from "@/components/ui";
import { cn } from "@/lib/utils";

const NAV = [
  { group: "Overview", items: [{ href: "/", label: "Dashboard", icon: LayoutDashboard }, { href: "/radar", label: "Global Radar", icon: Activity }] },
  { group: "Build", items: [{ href: "/playground", label: "Playground", icon: Terminal }] },
  { group: "Observe", items: [{ href: "/traces", label: "Traces", icon: Activity }] },
  {
    group: "Agents",
    items: [
      { href: "/agents", label: "Agents", icon: Bot },
      { href: "/approvals", label: "Approvals", icon: ShieldCheck },
    ],
  },
  {
    group: "Govern",
    items: [
      { href: "/policies", label: "Policies", icon: ScrollText },
      { href: "/budget", label: "Budget", icon: Gauge },
      { href: "/audit", label: "Audit", icon: ScrollText },
      { href: "/redteam", label: "Red Team", icon: ShieldCheck },
    ],
  },
  { group: "Evaluate", items: [{ href: "/evaluations", label: "Evaluations", icon: Gauge }] },
  { group: "System", items: [{ href: "/settings", label: "Settings", icon: Settings }] },
];

import { motion } from "framer-motion";

export function Sidebar({ mobileOpen, setMobileOpen }: { mobileOpen: boolean, setMobileOpen: (v: boolean) => void }) {
  const pathname = usePathname();
  
  const content = (
    <>
      <div className="flex items-center gap-3 border-b border-white/5 px-6 py-5">
        <div className="flex h-10 w-10 relative rounded-xl overflow-hidden shadow-[0_0_20px_rgba(124,58,237,0.4)] border border-white/10">
          <Image src="/prometheus-logo.jpg" alt="Prometheus Logo" fill className="object-cover" />
          <div className="absolute inset-0 bg-white/20 -translate-x-full animate-[shimmer_3s_infinite_linear]" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight leading-none text-foreground">Prometheus</p>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mt-1">AI Governance</p>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {NAV.map((group) => (
          <div key={group.group} className="animate-fade-in-up">
            <p className="px-2 mb-2 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50">{group.group}</p>
            <div className="space-y-1 relative">
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors duration-200 relative group z-10",
                      active ? "text-white" : "text-muted-foreground hover:text-white",
                    )}
                  >
                    {active && (
                      <motion.div 
                        layoutId="activeTab"
                        className="absolute inset-0 bg-accent/20 rounded-xl border border-accent/30 shadow-[0_0_15px_rgba(124,58,237,0.2)] z-[-1]" 
                        transition={{ type: "spring", stiffness: 400, damping: 30 }}
                      />
                    )}
                    <Icon size={18} className={cn("transition-transform duration-200", active ? "scale-110 drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]" : "group-hover:scale-110")} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-border/50 glass bg-background/60 lg:flex">
        {content}
      </aside>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div 
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden animate-in fade-in"
          onClick={() => setMobileOpen(false)}
        />
      )}
      
      {/* Mobile Sidebar */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 w-64 flex-col border-r border-border/50 glass bg-background/95 lg:hidden transition-transform duration-300 ease-out flex",
        mobileOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        {content}
      </aside>
    </>
  );
}

export function Topbar({ mode, killSwitch, setMobileOpen }: { mode: "live" | "mock" | "loading"; killSwitch?: string; setMobileOpen: (v: boolean) => void }) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => setMounted(true), []);
  
  const title = NAV.flatMap((g) => g.items).find((i) => i.href === pathname)?.label ?? "Dashboard";
  
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-border/50 glass bg-background/60 px-6 py-4 animate-slide-in-left">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" className="lg:hidden shrink-0 -ml-2" onClick={() => setMobileOpen(true)}>
          <Menu size={20} />
        </Button>
        <h1 className="text-xl font-bold tracking-tight">{title}</h1>
        <div className="hidden sm:flex items-center gap-2">
          {mode === "mock" ? (
            <Badge tone="amber">Demo mode</Badge>
          ) : (
            <Badge tone="green" className="animate-glow-pulse">Live API</Badge>
          )}
          {killSwitch && killSwitch !== "off" ? <Badge tone="redSolid" className="animate-pulse">Kill switch: {killSwitch}</Badge> : null}
        </div>
      </div>
      
      <div className="flex items-center gap-3">
        {mounted && (
          <Button 
            variant="outline" 
            size="icon" 
            className="rounded-full w-9 h-9"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? <Sun size={16} className="text-amber-400" /> : <Moon size={16} className="text-indigo-600" />}
          </Button>
        )}
      </div>
    </header>
  );
}
