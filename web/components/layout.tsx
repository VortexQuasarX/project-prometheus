"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { Activity, Bot, Gauge, LayoutDashboard, ScrollText, Settings, ShieldCheck, Terminal } from "lucide-react";
import { Badge, Button } from "@/components/ui";
import { cn } from "@/lib/utils";

const NAV = [
  { group: "Overview", items: [{ href: "/", label: "Dashboard", icon: LayoutDashboard }] },
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
    ],
  },
  { group: "Evaluate", items: [{ href: "/evaluations", label: "Evaluations", icon: Gauge }] },
  { group: "System", items: [{ href: "/settings", label: "Settings", icon: Settings }] },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 flex-col border-r border-border bg-card lg:flex">
      <div className="flex items-center gap-2 border-b border-border px-4 py-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-sm font-bold text-white">P</span>
        <div>
          <p className="text-sm font-semibold leading-none">Prometheus</p>
          <p className="text-xs text-muted-foreground">AI Governance</p>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto p-2">
        {NAV.map((group) => (
          <div key={group.group} className="mb-3">
            <p className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{group.group}</p>
            {group.items.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm",
                    active ? "bg-accent/10 font-medium text-accent" : "text-foreground/80 hover:bg-muted",
                  )}
                >
                  <Icon size={15} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}

export function Topbar({ mode, killSwitch }: { mode: "live" | "mock" | "loading"; killSwitch?: string }) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const title =
    NAV.flatMap((g) => g.items).find((i) => i.href === pathname)?.label ?? "Dashboard";
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-card/95 px-6 py-3 backdrop-blur">
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold">{title}</h1>
        {mode === "mock" ? (
          <Badge tone="amber">Demo mode: backend offline — showing sample data</Badge>
        ) : (
          <Badge tone="green">Live</Badge>
        )}
        {killSwitch && killSwitch !== "off" ? <Badge tone="red">Kill switch: {killSwitch}</Badge> : null}
      </div>
      <Button variant="ghost" size="sm" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
        {theme === "dark" ? "Light" : "Dark"}
      </Button>
    </header>
  );
}
