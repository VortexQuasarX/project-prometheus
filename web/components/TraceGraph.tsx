"use client";

import { useMemo } from "react";
import ReactFlow, { Background, Controls, Node, Edge, Position } from "reactflow";
import "reactflow/dist/style.css";
import { formatMs } from "@/lib/utils";

interface TraceEvent {
  name: string;
  status: string;
  duration_ms: number;
  metadata?: Record<string, any>;
  timestamp: string;
}

export function TraceGraph({ timeline }: { timeline: TraceEvent[] }) {
  const { nodes, edges } = useMemo(() => {
    const nds: Node[] = [];
    const eds: Edge[] = [];
    
    timeline.forEach((event, idx) => {
      const isError = event.status.toLowerCase() !== "success" && event.status.toLowerCase() !== "ok";
      const color = isError ? "#ef4444" : "#7c3aed";
      
      nds.push({
        id: `node-${idx}`,
        position: { x: 250, y: idx * 120 },
        data: {
          label: (
            <div className="flex flex-col gap-1 text-left min-w-[200px]">
              <div className="flex justify-between items-center">
                <span className="font-mono text-xs font-bold text-white">{event.name}</span>
                <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded-sm" style={{ backgroundColor: `${color}40`, color }}>{event.status}</span>
              </div>
              <span className="text-[10px] text-zinc-400 font-mono">{formatMs(event.duration_ms)}</span>
            </div>
          )
        },
        style: {
          background: "rgba(10, 10, 20, 0.8)",
          backdropFilter: "blur(8px)",
          border: `1px solid ${color}80`,
          borderRadius: "8px",
          color: "#fff",
          boxShadow: `0 4px 15px ${color}20`
        },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
      });

      if (idx > 0) {
        eds.push({
          id: `edge-${idx - 1}-${idx}`,
          source: `node-${idx - 1}`,
          target: `node-${idx}`,
          animated: true,
          style: { stroke: "#7c3aed", strokeWidth: 2 },
        });
      }
    });

    return { nodes: nds, edges: eds };
  }, [timeline]);

  return (
    <div className="h-[600px] w-full rounded-xl overflow-hidden border border-border/50 glass">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#7c3aed" gap={16} />
        <Controls className="fill-white bg-background border border-border/50" />
      </ReactFlow>
    </div>
  );
}
