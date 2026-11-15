"use client";

import React, { useState } from "react";
import { StudentSidebar } from "@/components/layout/StudentSidebar";
import { Search } from "lucide-react";

interface StudentLayoutProps {
  children: React.ReactNode;
}

export function StudentLayout({ children }: StudentLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-[#08090A] text-[#ECEEF0]">
      <StudentSidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />

      <div
        className={`min-h-screen flex flex-col transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] ${
          collapsed ? "ml-16" : "ml-64"
        }`}
      >
        {/* Full Desktop Topbar (h-14 to match Sidebar Header) */}
        <header className="sticky top-0 z-30 h-14 border-b border-white/[0.08] bg-[#08090A]/90 backdrop-blur-md px-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5 text-xs text-[#9DA3AE]">
            <span className="font-semibold text-xs text-[#FFFFFF]">BCREC Portal</span>
            <span className="text-[#6E7480]">/</span>
            <span>B.Tech CSE (Autonomous)</span>
            <span className="text-[#6E7480]">/</span>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-500/15 text-indigo-300 border border-indigo-500/25 font-semibold">
              Semester 5
            </span>
          </div>

          <div className="flex items-center gap-4">
            {/* Search Pill */}
            <div className="relative hidden sm:block">
              <div className="flex items-center gap-2 h-8 px-3 text-[13px] text-[#9DA3AE] bg-white/[0.04] border border-white/[0.08] rounded-lg">
                <Search className="w-3.5 h-3.5 text-[#8A8F98]" />
                <input
                  type="text"
                  placeholder="Search syllabus, notes, or PYQs..."
                  className="bg-transparent border-none outline-none text-xs text-white placeholder-[#6E7480] w-48"
                />
                <kbd className="inline-flex items-center px-1 text-[10px] font-mono text-[#8A8F98] bg-white/[0.06] rounded border border-white/[0.08]">
                  ⌘K
                </kbd>
              </div>
            </div>

            {/* Quick Status Pill */}
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-rose-500/10 border border-rose-500/25 text-[11px] font-mono text-rose-300">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping" />
              <span>DBMS: 73.3% · Urgent Recovery</span>
            </div>

            {/* Profile Avatar */}
            <div className="flex items-center gap-2.5 pl-3 border-l border-white/[0.08]">
              <div className="w-7 h-7 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-xs font-mono font-bold text-indigo-300">
                AR
              </div>
              <div className="hidden lg:block text-left text-xs leading-tight">
                <p className="font-semibold text-[#FFFFFF]">Ananya Roy</p>
                <p className="text-[11px] text-[#8A8F98]">Section A · 3rd Year</p>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content Container with Full Widescreen Desktop Grid */}
        <main className="flex-1 px-6 py-6 lg:px-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
