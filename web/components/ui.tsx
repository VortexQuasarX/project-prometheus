"use client";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-xl text-sm font-medium transition-all duration-300 disabled:pointer-events-none disabled:opacity-50 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
  {
    variants: {
      variant: {
        default: "bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:shadow-[0_0_15px_rgba(79,70,229,0.5)] hover:opacity-90",
        destructive: "bg-destructive text-white hover:bg-destructive/90",
        outline: "border border-border/50 glass hover:bg-muted/50",
        ghost: "hover:bg-muted/50",
        secondary: "bg-muted text-foreground hover:bg-muted/80",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 px-3 text-xs rounded-lg",
        lg: "h-12 px-8 rounded-2xl",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

import { motion } from "framer-motion";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement> & any) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.01, translateY: -4 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className={cn("glass-card gradient-border", className)} 
      {...props} 
    />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1.5 p-5 pb-3 z-10 relative", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-base font-semibold tracking-tight", className)} {...props} />;
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-xs text-muted-foreground leading-relaxed", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5 pt-0 z-10 relative", className)} {...props} />;
}

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase transition-colors border",
  {
    variants: {
      tone: {
        green: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
        amber: "bg-amber-500/10 text-amber-500 border-amber-500/20",
        amberOutline: "border-amber-500/40 text-amber-500 bg-transparent",
        red: "bg-red-500/10 text-red-500 border-red-500/20",
        redSolid: "bg-red-600 text-white border-red-600 shadow-[0_0_10px_rgba(220,38,38,0.4)]",
        blue: "bg-blue-500/10 text-blue-500 border-blue-500/20",
        purple: "bg-purple-500/10 text-purple-500 border-purple-500/20",
        gray: "bg-muted/50 text-muted-foreground border-border/50",
      },
    },
    defaultVariants: { tone: "gray" },
  },
);

export type BadgeTone = NonNullable<VariantProps<typeof badgeVariants>["tone"]>;

export function Badge({ className, tone, ...props }: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}

export function statusTone(status: string | null | undefined): BadgeTone {
  const s = (status ?? "").toLowerCase();
  if (["approved", "applied", "verified", "success", "normal", "ok", "hit"].includes(s)) return "green";
  if (["pending", "running", "warning", "cheap_only", "cheap_model"].includes(s)) return "amber";
  if (s === "waiting_approval") return "amberOutline";
  if (["rejected", "failed", "exceeded", "blocked", "reject", "critical", "block_all"].includes(s)) return "red";
  if (["cache_only", "cache_only_mode", "info", "masked"].includes(s)) return "blue";
  if (["strong_model"].includes(s)) return "purple";
  if (s === "critical_solid") return "redSolid";
  return "gray";
}

export function Progress({ value, className }: { value: number; className?: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const isDanger = pct >= 90;
  return (
    <div className={cn("h-2.5 w-full overflow-hidden rounded-full bg-muted/50 border border-border/20", className)}>
      <div 
        className={cn(
          "h-full rounded-full transition-all duration-1000 ease-out relative",
          isDanger ? "bg-red-500" : "bg-gradient-to-r from-blue-500 to-indigo-500"
        )} 
        style={{ width: `${pct}%` }} 
      >
        <div className="absolute inset-0 bg-white/20 animate-shimmer" />
      </div>
    </div>
  );
}

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("text-xs font-semibold uppercase tracking-wider text-muted-foreground", className)} {...props} />;
}

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn("h-10 w-full rounded-xl border border-border/50 bg-background/50 backdrop-blur-sm px-3 text-sm transition-all focus:border-accent focus:ring-1 focus:ring-accent outline-none", className)} {...props} />;
}

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn("w-full rounded-xl border border-border/50 bg-background/50 backdrop-blur-sm p-3 text-sm transition-all focus:border-accent focus:ring-1 focus:ring-accent outline-none resize-y", className)} {...props} />;
}

export function Select({ className, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn("h-10 w-full rounded-xl border border-border/50 bg-background/50 backdrop-blur-sm px-3 text-sm transition-all focus:border-accent focus:ring-1 focus:ring-accent outline-none appearance-none", className)} {...props}>
      {children}
    </select>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-muted/80 relative overflow-hidden", className)}>
    <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
  </div>;
}

export function EmptyState({ title, hint, icon }: { title: string; hint?: string; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border/50 bg-muted/10 p-12 text-center animate-fade-in-up">
      {icon && <div className="text-muted-foreground/50 animate-float">{icon}</div>}
      <div>
        <p className="text-base font-semibold">{title}</p>
        {hint ? <p className="text-sm text-muted-foreground mt-1">{hint}</p> : null}
      </div>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-500 animate-scale-in flex items-start gap-3">
      <svg className="w-5 h-5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
      <div>
        <p className="font-semibold">Error Encountered</p>
        <p className="opacity-80 mt-1">{message}</p>
      </div>
    </div>
  );
}

export function JsonViewer({ data }: { data: unknown }) {
  return (
    <pre className="max-h-64 overflow-auto rounded-xl bg-background/80 border border-border/50 p-4 text-[11px] leading-5 font-mono shadow-inner">
      <code className="text-muted-foreground">{JSON.stringify(data, null, 2)}</code>
    </pre>
  );
}

export function Table({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("overflow-x-auto rounded-xl border border-border/50 glass", className)}>
      <table className="w-full text-sm">{children}</table>
    </div>
  );
}

export function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return <th className={cn("bg-muted/30 px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b border-border/50", className)}>{children}</th>;
}

export function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn("px-4 py-3 align-middle", className)}>{children}</td>;
}

export function AnimatedCounter({ value, prefix = "", suffix = "", decimals = 0 }: { value: number, prefix?: string, suffix?: string, decimals?: number }) {
  const [displayValue, setDisplayValue] = useState(0);
  
  useEffect(() => {
    let start = displayValue;
    const end = value;
    if (start === end) return;
    
    const duration = 1000;
    const startTime = performance.now();
    
    const animate = (time: number) => {
      const elapsed = time - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function: easeOutQuart
      const ease = 1 - Math.pow(1 - progress, 4);
      
      setDisplayValue(start + (end - start) * ease);
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setDisplayValue(end);
      }
    };
    
    requestAnimationFrame(animate);
  }, [value]);
  
  return (
    <span>{prefix}{displayValue.toFixed(decimals)}{suffix}</span>
  );
}

export function MetricCard({
  label,
  value,
  sub,
  icon,
  gradient = false,
  ...props
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  icon?: React.ReactNode;
  gradient?: boolean;
  [key: string]: any;
}) {
  return (
    <Card {...props} className={cn("", gradient && "border-accent/30 shadow-[0_0_30px_rgba(124,58,237,0.15)] bg-gradient-to-br from-accent/10 via-transparent to-transparent")}>
      <CardContent className="p-5 flex flex-col h-full justify-between">
        <div className="flex justify-between items-start">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">{label}</p>
          {icon && <div className={cn("p-2 rounded-lg", gradient ? "bg-accent/20 text-accent" : "bg-muted text-muted-foreground")}>{icon}</div>}
        </div>
        <div>
          <p className={cn("tabular mt-1 text-3xl font-bold tracking-tight", gradient && "gradient-text")}>{value}</p>
          {sub ? <p className="mt-2 text-xs font-medium text-muted-foreground/80">{sub}</p> : null}
        </div>
      </CardContent>
    </Card>
  );
}
