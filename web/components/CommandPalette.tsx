"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { Activity, Terminal, Shield, Wallet, Play } from "lucide-react";
import { toast } from "sonner";
import { setKillSwitch } from "@/lib/api";
import useSound from "use-sound";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  // We use a generic UI click sound if one exists, otherwise fallback to empty string
  // To avoid build errors if the file doesn't exist, we'll gracefully ignore it.
  const [play] = useSound('/click.mp3', { volume: 0.25, interrupt: true });

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
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-start justify-center pt-[15vh]">
      <Command.Dialog 
        open={open} 
        onOpenChange={setOpen} 
        className="w-[90vw] max-w-[600px] bg-background/90 glass-card rounded-2xl overflow-hidden shadow-2xl border border-border/50"
      >
        <Command.Input 
          autoFocus
          placeholder="Type a command or search..." 
          className="w-full h-14 bg-transparent border-b border-border/50 px-4 text-sm outline-none placeholder:text-muted-foreground"
        />
        <Command.List className="max-h-[300px] overflow-y-auto p-2">
          <Command.Empty className="py-6 text-center text-sm text-muted-foreground">No results found.</Command.Empty>
          
          <Command.Group heading="Navigation" className="text-xs font-semibold text-muted-foreground px-2 py-1 uppercase tracking-wider">
            <Command.Item onSelect={() => { router.push("/playground"); setOpen(false); }} className="flex items-center gap-2 px-2 py-3 rounded-lg text-sm text-foreground hover:bg-muted/50 cursor-pointer">
              <Play size={16} /> Playground
            </Command.Item>
            <Command.Item onSelect={() => { router.push("/traces"); setOpen(false); }} className="flex items-center gap-2 px-2 py-3 rounded-lg text-sm text-foreground hover:bg-muted/50 cursor-pointer">
              <Activity size={16} /> Traces
            </Command.Item>
            <Command.Item onSelect={() => { router.push("/budget"); setOpen(false); }} className="flex items-center gap-2 px-2 py-3 rounded-lg text-sm text-foreground hover:bg-muted/50 cursor-pointer">
              <Wallet size={16} /> FinOps Budget
            </Command.Item>
            <Command.Item onSelect={() => { router.push("/policies"); setOpen(false); }} className="flex items-center gap-2 px-2 py-3 rounded-lg text-sm text-foreground hover:bg-muted/50 cursor-pointer">
              <Shield size={16} /> Governance Policies
            </Command.Item>
          </Command.Group>

          <Command.Group heading="Actions" className="text-xs font-semibold text-muted-foreground px-2 pt-4 pb-1 uppercase tracking-wider border-t border-border/50 mt-2">
            <Command.Item onSelect={() => { 
                setKillSwitch("block_all", "Triggered via Command Palette").then(() => {
                  toast.error("Kill Switch Activated: BLOCK ALL");
                  setOpen(false);
                });
              }} 
              className="flex items-center gap-2 px-2 py-3 rounded-lg text-sm text-red-500 hover:bg-red-500/10 cursor-pointer"
            >
              <Terminal size={16} /> Engage Full Kill Switch
            </Command.Item>
            <Command.Item onSelect={() => { 
                setKillSwitch("off", "Reset via Command Palette").then(() => {
                  toast.success("Kill Switch Disengaged");
                  setOpen(false);
                });
              }} className="px-3 py-2.5 rounded-lg flex items-center gap-3 text-sm cursor-pointer hover:bg-muted/80 text-emerald-500 font-medium">
                <Play size={16} /> Disengage Kill Switch (Resume Traffic)
              </Command.Item>
          </Command.Group>
        </Command.List>
      </Command.Dialog>
    </div>
  );
}
