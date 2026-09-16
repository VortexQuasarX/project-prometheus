import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "./providers";
import { cn } from "@/lib/utils";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Project Prometheus",
  description: "Agentic AI Governance and FinOps Control Plane",
};

import dynamic from 'next/dynamic';

const CommandPalette = dynamic(() => import("@/components/CommandPalette").then(mod => mod.CommandPalette), { ssr: false });
const Copilot = dynamic(() => import("@/components/Copilot").then(mod => mod.Copilot), { ssr: false });

import { Meteors } from "@/components/ui";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${inter.variable} font-sans`}>
      <body className={cn(inter.className, "min-h-screen bg-background relative overflow-x-hidden selection:bg-primary/20 selection:text-primary")}>
        
        {/* Animated Grid & Mesh Background */}
        <div className="fixed inset-0 z-[-2] pointer-events-none opacity-40 mix-blend-normal dark:mix-blend-screen transition-opacity duration-1000">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>
          <Meteors number={20} />
        </div>
        <div className="fixed inset-0 z-[-1] pointer-events-none transition-opacity duration-1000 opacity-60">
          <div className="absolute -top-[30%] -left-[10%] w-[50%] h-[50%] rounded-full bg-blue-500/10 blur-[120px] animate-pulse-slow" />
          <div className="absolute top-[20%] -right-[10%] w-[40%] h-[60%] rounded-full bg-purple-500/10 blur-[120px] animate-pulse-slow" style={{ animationDelay: "2s" }} />
        </div>

        <Providers>
          {children}
          <CommandPalette />
        </Providers>
      </body>
    </html>
  );
}
