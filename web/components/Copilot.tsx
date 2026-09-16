"use client";

import { useState } from "react";
import { MessageSquare, X, Send, Sparkles, BrainCircuit } from "lucide-react";
import { Button, Card, CardHeader, CardTitle, CardContent, Textarea } from "@/components/ui";

export function Copilot() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [chat, setChat] = useState<{ role: string; content: string }[]>([
    { role: "assistant", content: "I am Prometheus, your AI FinOps and Governance Co-pilot. Ask me about your spend, latency anomalies, or traffic." }
  ]);
  const [isThinking, setIsThinking] = useState(false);

  const handleSend = () => {
    if (!query.trim()) return;
    
    setChat(prev => [...prev, { role: "user", content: query }]);
    setQuery("");
    setIsThinking(true);

    // Simulate backend response
    setTimeout(() => {
      setChat(prev => [...prev, { 
        role: "assistant", 
        content: "Based on the latest telemetry, the p99 latency spike between 2:00 AM and 4:00 AM was caused by an autonomous script making 5,000 highly-complex reasoning requests to `us-east-1`." 
      }]);
      setIsThinking(false);
    }, 1500);
  };

  return (
    <>
      <Button
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-2xl bg-accent hover:bg-accent/90 border-2 border-accent-foreground/10 transition-transform ${isOpen ? 'scale-0' : 'scale-100'} z-40`}
      >
        <Sparkles size={24} className="text-white" />
      </Button>

      <div className={`fixed bottom-6 right-6 w-[400px] shadow-2xl transition-all duration-300 transform origin-bottom-right z-50 ${isOpen ? 'scale-100 opacity-100' : 'scale-0 opacity-0 pointer-events-none'}`}>
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
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                  msg.role === 'user' 
                    ? 'bg-accent text-white' 
                    : 'bg-muted/50 border border-border/50 text-foreground'
                }`}>
                  {msg.content}
                </div>
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
    </>
  );
}
