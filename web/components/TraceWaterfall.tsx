"use client";

import { useMemo, useState } from "react";
import { formatMs } from "@/lib/utils";
import { Clock, Shield, Terminal, Network, Cpu, Activity, CheckCircle2, AlertCircle } from "lucide-react";

interface TraceEvent {
  name: string;
  status: string;
  duration_ms: number;
  metadata?: Record<string, any>;
  timestamp: string;
}

const getStageMeta = (name: string) => {
  const lower = name.toLowerCase();
  if (lower.includes("guardrail") || lower.includes("pii") || lower.includes("safety")) {
    return { icon: Shield, color: "text-amber-500", barColor: "bg-gradient-to-r from-amber-500 to-orange-500" };
  }
  if (lower.includes("cache")) {
    return { icon: Terminal, color: "text-blue-500", barColor: "bg-gradient-to-r from-blue-500 to-cyan-500" };
  }
  if (lower.includes("router") || lower.includes("route") || lower.includes("policy")) {
    return { icon: Network, color: "text-purple-500", barColor: "bg-gradient-to-r from-purple-500 to-indigo-500" };
  }
  if (lower.includes("llm") || lower.includes("generate") || lower.includes("provider")) {
    return { icon: Cpu, color: "text-emerald-500", barColor: "bg-gradient-to-r from-emerald-500 to-teal-500" };
  }
  return { icon: Activity, color: "text-accent", barColor: "bg-gradient-to-r from-indigo-500 to-accent" };
};

export function TraceWaterfall({ timeline }: { timeline: TraceEvent[] }) {
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const { totalDuration, stages } = useMemo(() => {
    let offset = 0;
    const computed = (timeline || []).map((t) => {
      const dur = Math.max(0.1, t.duration_ms || 0);
      const start = offset;
      offset += dur;
      return {
        ...t,
        startOffset: start,
        duration: dur,
      };
    });
    return {
      totalDuration: Math.max(offset, 1),
      stages: computed,
    };
  }, [timeline]);

  if (!timeline || timeline.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-muted-foreground">
        No detailed stage events recorded for this trace.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Timeline Header & Scale Bar */}
      <div className="flex items-center justify-between text-xs text-muted-foreground border-b border-border/50 pb-2 px-2">
        <div className="flex items-center gap-2">
          <Clock size={14} className="text-accent" />
          <span className="font-semibold text-foreground">Pipeline Execution Waterfall</span>
          <span className="font-mono text-[11px]">({stages.length} stages • total {formatMs(totalDuration)})</span>
        </div>
        <div className="hidden sm:flex items-center gap-4 text-[10px] font-mono">
          <span>0ms</span>
          <span>{formatMs(totalDuration * 0.25)}</span>
          <span>{formatMs(totalDuration * 0.5)}</span>
          <span>{formatMs(totalDuration * 0.75)}</span>
          <span>{formatMs(totalDuration)}</span>
        </div>
      </div>

      {/* Waterfall Rows */}
      <div className="space-y-1.5 font-sans">
        {stages.map((stage, idx) => {
          const meta = getStageMeta(stage.name);
          const Icon = meta.icon;
          const leftPercent = (stage.startOffset / totalDuration) * 100;
          const widthPercent = Math.max(2, (stage.duration / totalDuration) * 100);
          const isSelected = selectedIdx === idx;
          const isSuccess = stage.status.toLowerCase() === "success" || stage.status.toLowerCase() === "ok";

          return (
            <div
              key={idx}
              onClick={() => setSelectedIdx(isSelected ? null : idx)}
              className={`group flex flex-col p-2.5 rounded-xl transition-all border cursor-pointer ${
                isSelected
                  ? "bg-accent/10 border-accent/40 shadow-sm"
                  : "bg-background/40 hover:bg-muted/30 border-transparent hover:border-border/50"
              }`}
            >
              <div className="flex items-center justify-between text-xs mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="p-1 rounded-md bg-muted/40">
                    <Icon size={12} className={meta.color} />
                  </span>
                  <span className="font-mono font-semibold text-foreground text-xs">{stage.name}</span>
                  {isSuccess ? (
                    <span className="inline-flex items-center gap-0.5 text-[10px] text-emerald-500 font-medium">
                      <CheckCircle2 size={10} /> {stage.status}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-0.5 text-[10px] text-red-500 font-medium">
                      <AlertCircle size={10} /> {stage.status}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 font-mono text-[11px]">
                  <span className="text-muted-foreground text-[10px]">
                    {((stage.duration / totalDuration) * 100).toFixed(1)}%
                  </span>
                  <span className="font-semibold text-foreground">{formatMs(stage.duration)}</span>
                </div>
              </div>

              {/* Gantt Bar Background & Fill */}
              <div className="relative h-2.5 w-full rounded-full bg-muted/30 overflow-hidden">
                <div
                  className={`absolute top-0 bottom-0 rounded-full ${meta.barColor} transition-all duration-300 shadow-sm group-hover:brightness-110`}
                  style={{
                    left: `${Math.min(98, leftPercent)}%`,
                    width: `${Math.min(100 - leftPercent, widthPercent)}%`,
                  }}
                />
              </div>

              {/* Collapsible Metadata Drawer on Click */}
              {isSelected && stage.metadata && Object.keys(stage.metadata).length > 0 && (
                <div className="mt-2.5 p-3 rounded-lg bg-background/80 border border-border/50 text-[11px] font-mono space-y-1 animate-in fade-in duration-150">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">Stage Metadata</p>
                  <pre className="overflow-x-auto text-foreground whitespace-pre-wrap max-h-40 text-[10px]">
                    {JSON.stringify(stage.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
