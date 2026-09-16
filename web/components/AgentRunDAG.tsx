"use client";

import { useMemo } from "react";
import ReactFlow, { Background, Controls, Node, Edge, Position } from "reactflow";
import "reactflow/dist/style.css";
import { formatMs } from "@/lib/utils";

interface ToolCall {
  tool: string;
  duration_ms: number;
  status: string;
  input?: any;
  output?: any;
}

export function AgentRunDAG({ toolCalls, trigger = "manual" }: { toolCalls: ToolCall[]; trigger?: string }) {
  const { nodes, edges } = useMemo(() => {
    const nds: Node[] = [];
    const eds: Edge[] = [];

    // Root node: Trigger
    nds.push({
      id: "node-trigger",
      position: { x: 200, y: 20 },
      data: {
        label: (
          <div className="p-2 text-left min-w-[180px]">
            <span className="text-[9px] uppercase font-bold text-muted-foreground block">Event Trigger</span>
            <span className="font-mono text-xs font-bold text-foreground capitalize">{trigger} Influx</span>
          </div>
        ),
      },
      style: {
        background: "rgba(30, 41, 59, 0.8)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(148, 163, 184, 0.3)",
        borderRadius: "12px",
        color: "#fff",
      },
      sourcePosition: Position.Bottom,
    });

    let prevId = "node-trigger";

    (toolCalls || []).forEach((tc, idx) => {
      const nodeId = `node-tool-${idx}`;
      const isSuccess = tc.status === "success" || tc.status === "ok";
      const color = isSuccess ? "#10b981" : "#ef4444";
      const yPos = 130 + idx * 100;
      // Stagger slightly left and right for visual appeal
      const xPos = 200 + (idx % 2 === 0 ? -20 : 20);

      nds.push({
        id: nodeId,
        position: { x: xPos, y: yPos },
        data: {
          label: (
            <div className="p-2 text-left min-w-[210px]">
              <div className="flex justify-between items-center mb-1">
                <span className="font-mono text-xs font-bold text-accent">{tc.tool}</span>
                <span
                  className="text-[9px] font-bold px-1.5 py-0.5 rounded"
                  style={{ backgroundColor: `${color}25`, color }}
                >
                  {tc.status}
                </span>
              </div>
              <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
                <span>Step {idx + 1}</span>
                <span>{formatMs(tc.duration_ms)}</span>
              </div>
            </div>
          ),
        },
        style: {
          background: "rgba(15, 23, 42, 0.85)",
          backdropFilter: "blur(12px)",
          border: `1px solid ${color}60`,
          borderRadius: "12px",
          color: "#fff",
          boxShadow: `0 4px 20px ${color}15`,
        },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
      });

      eds.push({
        id: `edge-${prevId}-${nodeId}`,
        source: prevId,
        target: nodeId,
        animated: true,
        style: { stroke: "#6366f1", strokeWidth: 2 },
      });

      prevId = nodeId;
    });

    return { nodes: nds, edges: eds };
  }, [toolCalls, trigger]);

  if (!toolCalls || toolCalls.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-muted-foreground">
        No agent step DAG recorded for this execution.
      </div>
    );
  }

  return (
    <div className="h-[480px] w-full rounded-2xl overflow-hidden border border-border/50 bg-background/50 relative">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#6366f1" gap={16} size={1} />
        <Controls className="fill-foreground bg-background border border-border/50 rounded-xl" />
      </ReactFlow>
    </div>
  );
}
