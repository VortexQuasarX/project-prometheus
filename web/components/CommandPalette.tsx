"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { Activity, Terminal, Shield, Wallet, Play, Sparkles, Cpu, Zap, Search } from "lucide-react";
import { toast } from "sonner";
import { setKillSwitch } from "@/lib/api";

import { useQuery } from "@tanstack/react-query";
import { getTraces, getPolicies, getPendingActions } from "@/lib/api";
import { formatTime } from "@/lib/utils";

import useSound from "use-sound";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const [play] = useSound('/click.mp3', { volume: 0.25, interrupt: true });

  const [query, setQuery] = useState("");
  
  const { data: traces } = useQuery({ queryKey: ["traces", "search"], queryFn: () => getTraces(10), enabled: open });
  const { data: actions } = useQuery({ queryKey: ["actions", "search"], queryFn: getPendingActions, enabled: open });


  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => {
          if (!open) {
            try { play(); } catch(err) {}
          }
          return !open;
        });
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-background/60 backdrop-blur-md flex items-start justify-center pt-[15vh] animate-in fade-in duration-200" onClick={() => setOpen(false)}>
      <div className="w-[90vw] max-w-[650px] relative" onClick={e => e.stopPropagation()}>
        <Command 
          className="w-full bg-card/95 backdrop-blur-xl rounded-2xl overflow-hidden shadow-[0_0_80px_rgba(var(--primary),0.15)] border border-border/80 magic-border-container animate-in zoom-in-95 duration-200"
        >
          <div className="magic-border-inner" />
          
          <div className="relative z-10 flex items-center border-b border-border/50 px-4">
          <Search className="w-5 h-5 text-accent" />
          <Command.Input 
            autoFocus
            value={query}
            onValueChange={setQuery}
            placeholder="Type a command or search (e.g. 'budget', 'kill switch')..." 
            className="w-full h-16 bg-transparent px-4 text-base outline-none placeholder:text-muted-foreground/60 text-foreground font-medium"
          />
          <div className="flex gap-1">
             <kbd className="bg-muted/50 text-muted-foreground px-2 py-1 rounded text-[10px] font-semibold tracking-widest border border-border/50">ESC</kbd>
          </div>
        </div>
        
        <Command.List className="max-h-[400px] overflow-y-auto p-2 relative z-10 scrollbar-hide">
          <Command.Empty className="py-12 text-center text-sm text-muted-foreground">
            <Sparkles className="w-8 h-8 mx-auto mb-3 opacity-20" />
            No results found for that query.
          </Command.Empty>
          
          <Command.Group heading="Navigation" className="text-xs font-bold text-muted-foreground/70 px-2 pt-3 pb-2 uppercase tracking-widest">
            <Command.Item onSelect={() => { router.push("/playground"); setOpen(false); }} className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm text-foreground/80 hover:text-foreground hover:bg-primary/10 hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] transition-all cursor-pointer group">
              <div className="p-2 bg-background/50 rounded-lg group-hover:scale-110 transition-transform shadow-sm"><Play size={16} className="text-accent"/></div>
              <div className="flex flex-col"><span className="font-semibold">Playground</span><span className="text-[10px] text-muted-foreground">Test models through the governance proxy</span></div>
            </Command.Item>
            <Command.Item onSelect={() => { router.push("/traces"); setOpen(false); }} className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm text-foreground/80 hover:text-foreground hover:bg-primary/10 hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] transition-all cursor-pointer group">
              <div className="p-2 bg-background/50 rounded-lg group-hover:scale-110 transition-transform shadow-sm"><Activity size={16} className="text-accent"/></div>
              <div className="flex flex-col"><span className="font-semibold">Traces & Logs</span><span className="text-[10px] text-muted-foreground">View telemetry and router decisions</span></div>
            </Command.Item>
            <Command.Item onSelect={() => { router.push("/budget"); setOpen(false); }} className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm text-foreground/80 hover:text-foreground hover:bg-primary/10 hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] transition-all cursor-pointer group">
              <div className="p-2 bg-background/50 rounded-lg group-hover:scale-110 transition-transform shadow-sm"><Wallet size={16} className="text-accent"/></div>
              <div className="flex flex-col"><span className="font-semibold">FinOps Budget</span><span className="text-[10px] text-muted-foreground">Manage organizational cost limits</span></div>
            </Command.Item>
            <Command.Item onSelect={() => { router.push("/policies"); setOpen(false); }} className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm text-foreground/80 hover:text-foreground hover:bg-primary/10 hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] transition-all cursor-pointer group">
              <div className="p-2 bg-background/50 rounded-lg group-hover:scale-110 transition-transform shadow-sm"><Shield size={16} className="text-accent"/></div>
              <div className="flex flex-col"><span className="font-semibold">Governance</span><span className="text-[10px] text-muted-foreground">Adjust router rules and failovers</span></div>
            </Command.Item>
            <Command.Item onSelect={() => { router.push("/agents"); setOpen(false); }} className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm text-foreground/80 hover:text-foreground hover:bg-primary/10 hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] transition-all cursor-pointer group">
              <div className="p-2 bg-background/50 rounded-lg group-hover:scale-110 transition-transform shadow-sm"><Cpu size={16} className="text-accent"/></div>
              <div className="flex flex-col"><span className="font-semibold">Autonomous Agents</span><span className="text-[10px] text-muted-foreground">Configure FinOps AI optimization</span></div>
            </Command.Item>
          </Command.Group>


          {traces?.items && traces.items.length > 0 && (
            <Command.Group heading="Recent Traces" className="text-xs font-bold text-muted-foreground/70 px-2 pt-4 pb-2 uppercase tracking-widest border-t border-border/50 mt-2">
              {traces.items.slice(0, 5).map(trace => (
                <Command.Item key={"trace-"+trace.request_id} onSelect={() => { router.push(`/traces/${trace.request_id}`); setOpen(false); }} className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm text-foreground/80 hover:text-foreground hover:bg-primary/10 hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] transition-all cursor-pointer group">
                  <div className="p-2 bg-purple-500/10 rounded-lg group-hover:scale-110 transition-transform shadow-sm"><Activity size={16} className="text-purple-500"/></div>
                  <div className="flex flex-col"><span className="font-semibold text-xs">{trace.request_id}</span><span className="text-[10px] text-muted-foreground">{trace.model} • {formatTime(trace.created_at)}</span></div>
                </Command.Item>
              ))}
            </Command.Group>
          )}

          {actions?.items && actions.items.length > 0 && (
            <Command.Group heading="Pending AI Actions" className="text-xs font-bold text-muted-foreground/70 px-2 pt-4 pb-2 uppercase tracking-widest border-t border-border/50 mt-2">
              {actions.items.map(action => (
                <Command.Item key={"action-"+action.action_id} onSelect={() => { router.push(`/approvals`); setOpen(false); }} className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm text-foreground/80 hover:text-foreground hover:bg-primary/10 hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] transition-all cursor-pointer group">
                  <div className="p-2 bg-amber-500/10 rounded-lg group-hover:scale-110 transition-transform shadow-sm"><Shield size={16} className="text-amber-500"/></div>
                  <div className="flex flex-col"><span className="font-semibold text-xs">{action.title}</span><span className="text-[10px] text-muted-foreground">{action.risk_level} Risk • Requires Approval</span></div>
                </Command.Item>
              ))}
            </Command.Group>
          )}
          <Command.Group heading="Critical Actions" className="text-xs font-bold text-muted-foreground/70 px-2 pt-4 pb-2 uppercase tracking-widest border-t border-border/50 mt-2">
            <Command.Item onSelect={() => { 
                setKillSwitch("block_all", "Triggered via Command Palette").then(() => {
                  toast.error("Kill Switch Activated: BLOCK ALL");
                  setOpen(false);
                });
              }} 
              className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm text-red-500 hover:bg-red-500/20 hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] transition-all cursor-pointer group"
            >
              <div className="p-2 bg-red-500/10 rounded-lg group-hover:scale-110 transition-transform shadow-sm"><Terminal size={16} className="text-red-500"/></div>
              <div className="flex flex-col"><span className="font-semibold">Engage Full Kill Switch</span><span className="text-[10px] text-red-500/80">Instantly halt all LLM egress traffic</span></div>
            </Command.Item>
            
            <Command.Item onSelect={() => { 
                setKillSwitch("off", "Reset via Command Palette").then(() => {
                  toast.success("Kill Switch Disengaged");
                  setOpen(false);
                });
              }} 
              className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm text-emerald-500 hover:bg-emerald-500/10 hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] transition-all cursor-pointer group"
            >
              <div className="p-2 bg-emerald-500/10 rounded-lg group-hover:scale-110 transition-transform shadow-sm"><Zap size={16} className="text-emerald-500"/></div>
              <div className="flex flex-col"><span className="font-semibold">Disengage Kill Switch</span><span className="text-[10px] text-emerald-500/80">Resume normal gateway operations</span></div>
            </Command.Item>
          </Command.Group>
        </Command.List>
        </Command>
      </div>
    </div>
  );
}
