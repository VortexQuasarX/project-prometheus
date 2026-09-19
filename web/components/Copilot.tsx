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

      <div className={`absolute top-12 right-0 w-[400px] shadow-2xl transition-all duration-200 transform origin-top-right z-[100] ${isOpen ? 'scale-100 opacity-100' : 'scale-95 opacity-0 pointer-events-none'}`}>
        <Card className="border border-border/50 bg-background/95 backdrop-blur-xl shadow-2xl flex flex-col h-[500px]">
          <CardHeader className="border-b border-border/50 bg-muted/30 py-3 px-4 flex flex-row items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <BrainCircuit size={16} className="text-accent" /> Ask Prometheus
            </CardTitle>
            <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full hover:bg-muted" onClick={() => setIsOpen(false)}>
              <X size={14} />
            </Button>
          </CardHeader>
          
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
            {chat.map((msg, i) => (
              <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`max-w-[90%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                  msg.role === 'user' 
                    ? 'bg-accent text-white' 
                    : 'bg-muted/50 border border-border/50 text-foreground'
                }`}>
                  {msg.content}
                </div>
                {msg.role === 'assistant' && msg.model && (
                  <div className="flex items-center gap-2 mt-1 px-1 text-[10px] text-muted-foreground font-mono">
                    <span>{msg.model}</span>
                    <span>•</span>
                    <span>{msg.latency_ms}ms</span>
                    {msg.cache_hit && (
                      <>
                        <span>•</span>
                        <span className="text-emerald-500 font-semibold flex items-center gap-0.5">
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
                <div className="max-w-[85%] rounded-2xl px-4 py-3 bg-muted/50 border border-border/50 text-foreground flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </CardContent>

          <div className="p-3 border-t border-border/50 bg-muted/10">
            <div className="relative">
              <Textarea 
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask about governance and FinOps..."
                className="min-h-[50px] resize-none rounded-xl pr-12 text-sm bg-background border-border/50"
              />
              <Button 
                size="icon" 
                className="absolute right-2 bottom-2 h-8 w-8 rounded-lg bg-accent hover:bg-accent/90"
                onClick={handleSend}
                disabled={!query.trim() || isThinking}
              >
                <Send size={14} className="text-white" />
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
