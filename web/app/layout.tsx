import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Project Prometheus",
  description: "Agentic AI Governance and FinOps Control Plane",
};

import dynamic from 'next/dynamic';

const CommandPalette = dynamic(() => import("@/components/CommandPalette").then(mod => mod.CommandPalette), { ssr: false });
const Copilot = dynamic(() => import("@/components/Copilot").then(mod => mod.Copilot), { ssr: false });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${inter.variable} font-sans`}>
      <body className="bg-background min-h-screen relative overflow-x-hidden">
        {/* Animated Background */}
        <div className="fixed inset-0 z-[-1] overflow-hidden pointer-events-none">
          <div className="absolute top-[-10%] left-[-10%] w-[40vw] h-[40vw] rounded-full bg-purple-600/10 blur-[100px] animate-blob"></div>
          <div className="absolute top-[20%] right-[-10%] w-[35vw] h-[35vw] rounded-full bg-cyan-600/10 blur-[100px] animate-blob" style={{ animationDelay: "2s" }}></div>
          <div className="absolute bottom-[-10%] left-[20%] w-[45vw] h-[45vw] rounded-full bg-blue-600/10 blur-[120px] animate-blob" style={{ animationDelay: "4s" }}></div>
        </div>
        <Providers>{children}</Providers>
        <CommandPalette />
        <Copilot />
      </body>
    </html>
  );
}
