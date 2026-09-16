"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/page-shell";
import { Badge, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import { Activity, Globe2, ShieldAlert, Zap } from "lucide-react";

import { CobeGlobe } from "@/components/CobeGlobe";

const TARGETS = [
  { lat: 38.03, lng: -78.47, name: "us-east-1" },
  { lat: 45.83, lng: -119.7, name: "us-west-2" },
  { lat: 50.11, lng: 8.68, name: "eu-central-1" },
  { lat: 35.68, lng: 139.69, name: "ap-northeast-1" },
  { lat: 19.07, lng: 72.87, name: "ap-south-1" },
];

export default function RadarPage() {
  return (
    <PageShell>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-8rem)]">
        
        {/* Radar View (3 Cols) */}
        <Card className="lg:col-span-3 border-accent/20 overflow-hidden relative glass bg-black flex items-center justify-center">
          <div className="absolute top-6 left-6 z-10 pointer-events-none">
            <h2 className="text-xl font-bold tracking-tight flex items-center gap-2 text-white">
              <Globe2 className="text-accent" /> Live Global Traffic Radar
            </h2>
            <p className="text-xs text-zinc-400 mt-1 uppercase tracking-wider font-mono flex items-center gap-2">
              Monitoring incoming requests to AWS Bedrock
            </p>
          </div>

          <CobeGlobe />
        </Card>

        {/* Telemetry Pane (1 Col) */}
        <Card className="flex flex-col h-full bg-background/80 backdrop-blur-md">
          <CardHeader className="border-b border-border/50">
            <CardTitle className="flex items-center gap-2"><Activity size={18} /> NOC Telemetry</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 p-5 space-y-6 overflow-y-auto">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Live Throughput</p>
              <div className="text-4xl font-mono font-bold text-emerald-500 flex items-baseline gap-2">
                4,210 <span className="text-sm text-muted-foreground uppercase tracking-wider">req/min</span>
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Active Regions</p>
              {TARGETS.map(t => (
                <div key={t.name} className="flex justify-between items-center bg-muted/20 p-2 rounded-md border border-border/30">
                  <span className="font-mono text-xs">{t.name}</span>
                  <Badge tone="green">Healthy</Badge>
                </div>
              ))}
            </div>

            <div className="pt-4 border-t border-border/50">
              <p className="text-xs font-semibold uppercase tracking-wider text-red-500 flex items-center gap-1 mb-3">
                <ShieldAlert size={14} /> Threats Intercepted (Last 1hr)
              </p>
              <div className="text-2xl font-mono font-bold text-red-500">142</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </PageShell>
  );
}
