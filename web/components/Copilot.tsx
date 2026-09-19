"use client";

import { useState, useRef, useEffect } from "react";
import { MessageSquare, X, Send, Sparkles, BrainCircuit, Zap } from "lucide-react";
import { Button, Card, CardHeader, CardTitle, CardContent, Textarea } from "@/components/ui";
import { postChat } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  model?: string;
  latency_ms?: number;
  cost_usd?: number;
  cache_hit?: boolean;
}

export function Copilot() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [chat, setChat] = useState<ChatMessage[]>([
    { role: "assistant", content: "I am Prometheus, your AI FinOps and Governance Co-pilot. Ask me about your spend, latency anomalies, or traffic." }
  ]);
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [chat, isOpen]);

  const handleSend = async () => {
    const trimmed = query.trim();
    if (!trimmed || isThinking) return;
    
    setChat(prev => [...prev, { role: "user", content: trimmed }]);
    setQuery("");
    setIsThinking(true);

    try {
      const res = await postChat({ query: trimmed });
      setChat(prev => [...prev, { 
        role: "assistant", 
        content: res.answer || "I received your request, but no text was returned.",
        model: res.model,
        latency_ms: res.latency_ms,
        cost_usd: res.estimated_cost_usd,
        cache_hit: res.cache_hit,
      }]);
    } catch (err: any) {
      setChat(prev => [...prev, { 
        role: "assistant", 
        content: `Error contacting Prometheus engine: ${err.message || "Failed to reach AI service."}` 
      }]);
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className="relative">
      <Button
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        className="gap-2 h-9 border-accent/20 bg-accent/5 hover:bg-accent/10 text-accent relative overflow-hidden group"
      >
        <Sparkles size={16} className="text-accent group-hover:animate-pulse" />
        <span className="hidden sm:inline">Ask AI</span>
      </Button>

      <div 
        className={`fixed sm:absolute top-16 right-2 sm:right-0 w-[calc(100vw-1rem)] sm:w-[430px] max-w-[95vw] shadow-2xl transition-all duration-200 transform origin-top-right z-[150] rounded-2xl border border-border/80 text-foreground flex flex-col h-[520px] overflow-hidden ${
          isOpen ? 'scale-100 opacity-100' : 'scale-95 opacity-0 pointer-events-none'
        }`}
        style={{ backgroundColor: '#0c111c' }}
      >
        {/* Solid Header */}
        <div className="border-b border-border/60 bg-[#121927] py-3.5 px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-accent/20 text-accent">
              <BrainCircuit size={17} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white leading-none">Ask Prometheus</h3>
              <p className="text-[11px] text-muted-foreground mt-0.5">Amazon Bedrock • FinOps Copilot</p>
            </div>
          </div>
          <button 
            onClick={() => setIsOpen(false)}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>
        
        {/* Scrollable Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#090d16]">
          {chat.map((msg, i) => (
            <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`max-w-[88%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${
                msg.role === 'user' 
                  ? 'bg-accent text-white shadow-md' 
                  : 'bg-[#151d2c] border border-border/60 text-slate-100 shadow-sm'
              }`}>
                {msg.content}
              </div>
              {msg.role === 'assistant' && msg.model && (
                <div className="flex items-center gap-2 mt-1 px-1 text-[10px] text-muted-foreground font-mono">
                  <span className="text-accent/90">{msg.model}</span>
                  <span>•</span>
                  <span>{msg.latency_ms}ms</span>
                  {msg.cache_hit && (
                    <>
                      <span>•</span>
                      <span className="text-emerald-400 font-semibold flex items-center gap-0.5">
                        <Zap size={10} /> Cache Hit
                      </span>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
          {isThinking && (
            <div className="flex justify-start">
              <div className="rounded-2xl px-4 py-3 bg-[#151d2c] border border-border/60 text-foreground flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: '300ms' }} />
                <span className="text-xs text-muted-foreground ml-1.5">Thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-border/60 bg-[#121927] shrink-0">
          <div className="flex items-center gap-2 bg-[#182133] border border-border/70 rounded-xl px-3 py-1.5 focus-within:border-accent transition-colors">
            <input 
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask about governance, spend, or policies..."
              className="flex-1 bg-transparent text-sm text-white placeholder:text-muted-foreground/70 outline-none py-1"
            />
            <button 
              type="button"
              onClick={handleSend}
              disabled={!query.trim() || isThinking}
              className="h-8 w-8 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center text-white shrink-0 transition-all shadow-sm"
              title="Send"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
