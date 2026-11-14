"use client";

import React from "react";
import Link from "next/link";
import { BottomNavigation } from "@/components/BottomNavigation";


interface MobileLayoutProps {
  children: React.ReactNode;
}

export function MobileLayout({ children }: MobileLayoutProps) {
  return (
    <div className="min-h-screen bg-[#08090A] text-[#ECEEF0] flex flex-col antialiased selection:bg-[#5E6AD2]/30 selection:text-white">
      {/* Top Precision Bar */}
      <header className="sticky top-0 z-40 h-13 border-b border-white/[0.08] bg-[#0D0E10]/90 backdrop-blur-md px-4 flex items-center justify-between">
        <div className="max-w-3xl w-full mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-5 h-5 rounded bg-[#5E6AD2] flex items-center justify-center text-white shadow-sm">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2" />
              </svg>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-xs tracking-tight text-white">ASPIRE</span>
              <span className="text-[10px] text-[#8A8F98] font-mono px-1 py-0.2 rounded bg-white/[0.04] border border-white/[0.06]">
                STUDENT
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 text-xs text-[#9DA3AE]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>BCREC Durgapur · CSE Sem 5</span>
            </div>
            <div className="flex items-center gap-1.5 pl-2 border-l border-white/[0.08]">
              <div className="w-6 h-6 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-[10px] font-mono text-indigo-300 font-semibold">
                AR
              </div>
              <span className="text-xs text-white font-medium hidden sm:inline">Ananya Roy</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-5 pb-24">
        {children}
      </main>

      {/* Sleek Bottom Navigation */}
      <BottomNavigation />
    </div>
  );
}
