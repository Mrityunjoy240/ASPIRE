"use client";

import React, { useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { CommandPalette } from "@/components/ui/CommandPalette";
import { Search } from "lucide-react";

interface WebLayoutProps {
  children: React.ReactNode;
}

export function WebLayout({ children }: WebLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);

  const openSearch = () => {
    // Trigger CommandPalette by dispatching KeyboardEvent
    const event = new KeyboardEvent("keydown", {
      key: "k",
      metaKey: true,
      bubbles: true,
    });
    document.dispatchEvent(event);
  };

  return (
    <div className="min-h-screen bg-[#08090A] text-[#ECEEF0]">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <CommandPalette />

      <div
        className={`min-h-screen flex flex-col transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] ${
          collapsed ? "ml-16" : "ml-64"
        }`}
      >
        {/* Balanced Topbar — Exactly h-14 to match Sidebar Header */}
        <header className="sticky top-0 z-30 h-14 border-b border-white/[0.08] bg-[#08090A]/90 backdrop-blur-md px-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5 text-sm text-[#9DA3AE]">
            <span className="font-semibold text-sm text-[#FFFFFF]">BCREC Workspace</span>
            <span className="text-[#6E7480]">/</span>
            <span>Academic Year 2026–27</span>
            <span className="text-[#6E7480]">/</span>
            <span className="px-2 py-0.5 rounded text-xs font-mono bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 font-semibold">
              Sem 5 Live
            </span>
          </div>

          <div className="flex items-center gap-4">
            {/* Linear-style Cmd+K search pill button */}
            <button
              onClick={openSearch}
              className="flex items-center gap-2.5 h-8 px-3 text-[13px] text-[#9DA3AE] hover:text-[#FFFFFF] bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.09] hover:border-white/[0.18] rounded-lg transition-all group"
            >
              <Search className="w-4 h-4 text-[#8A8F98] group-hover:text-white transition-colors" />
              <span className="hidden sm:inline font-medium">Search or jump to...</span>
              <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-mono text-[#9DA3AE] bg-white/[0.08] rounded border border-white/[0.10]">
                ⌘K
              </kbd>
            </button>

            <div className="flex items-center gap-3 pl-3 border-l border-white/[0.08]">
              <div className="w-7 h-7 rounded-full bg-[#5E6AD2]/20 border border-[#5E6AD2]/40 flex items-center justify-center text-xs font-bold text-[#A5AEF6]">
                AS
              </div>
              <div className="hidden md:block text-left text-sm leading-tight">
                <p className="font-semibold text-[#FFFFFF]">Dr. A. Sen</p>
                <p className="text-xs text-[#8A8F98]">Faculty Mentor</p>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content Container with balanced breathing room */}
        <main className="flex-1 px-6 py-8 lg:px-10 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
