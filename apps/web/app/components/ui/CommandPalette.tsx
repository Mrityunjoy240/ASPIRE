"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
  Search,
  LayoutDashboard,
  Inbox,
  BarChart3,
  Users,
  Building2,
  AlertTriangle,
  ArrowRight,
  Sparkles,
} from "lucide-react";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = (command: () => void) => {
    setOpen(false);
    command();
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-[15vh] px-4 animate-in fade-in duration-150"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-xl bg-[#121316] border border-white/[0.12] rounded-xl shadow-2xl overflow-hidden text-[#ECEEF0] animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        <Command className="w-full">
          <div className="flex items-center px-4 border-b border-white/[0.08] bg-[#16171A]">
            <Search className="w-4 h-4 text-[#8A8F98] mr-3 flex-shrink-0" />
            <Command.Input
              autoFocus
              placeholder="Type a command or search..."
              className="w-full bg-transparent py-3.5 text-sm text-[#FFFFFF] placeholder:text-[#6E7480] outline-none"
            />
            <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-0.5 text-xs font-mono text-[#8A8F98] bg-white/[0.06] rounded border border-white/[0.08]">
              ESC
            </kbd>
          </div>

          <Command.List className="p-2.5 max-h-80 overflow-y-auto space-y-1">
            <Command.Empty className="py-8 text-center text-sm text-[#8A8F98]">
              No results found for that query.
            </Command.Empty>

            <Command.Group heading="Navigation" className="text-xs font-mono font-semibold text-[#8A8F98] uppercase tracking-wider px-2 py-1.5">
              <Command.Item
                onSelect={() => runCommand(() => router.push("/"))}
                className="flex items-center justify-between px-3 py-2.5 text-sm rounded-lg cursor-pointer hover:bg-white/[0.06] aria-selected:bg-white/[0.08] aria-selected:text-[#FFFFFF] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <LayoutDashboard className="w-4 h-4 text-[#8A8F98]" />
                  <span>Command Center</span>
                </div>
                <ArrowRight className="w-4 h-4 text-[#6E7480]" />
              </Command.Item>

              <Command.Item
                onSelect={() => runCommand(() => router.push("/queue"))}
                className="flex items-center justify-between px-3 py-2.5 text-sm rounded-lg cursor-pointer hover:bg-white/[0.06] aria-selected:bg-white/[0.08] aria-selected:text-[#FFFFFF] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Inbox className="w-4 h-4 text-rose-400" />
                  <span>Triage Queue</span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-rose-500/15 text-rose-400 font-bold">10 Pending</span>
                </div>
                <ArrowRight className="w-4 h-4 text-[#6E7480]" />
              </Command.Item>

              <Command.Item
                onSelect={() => runCommand(() => router.push("/students"))}
                className="flex items-center justify-between px-3 py-2.5 text-sm rounded-lg cursor-pointer hover:bg-white/[0.06] aria-selected:bg-white/[0.08] aria-selected:text-[#FFFFFF] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Users className="w-4 h-4 text-[#8A8F98]" />
                  <span>Student Directory</span>
                </div>
                <ArrowRight className="w-4 h-4 text-[#6E7480]" />
              </Command.Item>

              <Command.Item
                onSelect={() => runCommand(() => router.push("/analytics"))}
                className="flex items-center justify-between px-3 py-2.5 text-sm rounded-lg cursor-pointer hover:bg-white/[0.06] aria-selected:bg-white/[0.08] aria-selected:text-[#FFFFFF] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <BarChart3 className="w-4 h-4 text-[#8A8F98]" />
                  <span>Institutional Analytics</span>
                </div>
                <ArrowRight className="w-4 h-4 text-[#6E7480]" />
              </Command.Item>

              <Command.Item
                onSelect={() => runCommand(() => router.push("/admin/institutions"))}
                className="flex items-center justify-between px-3 py-2.5 text-sm rounded-lg cursor-pointer hover:bg-white/[0.06] aria-selected:bg-white/[0.08] aria-selected:text-[#FFFFFF] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Building2 className="w-4 h-4 text-[#8A8F98]" />
                  <span>Institution Rules Control</span>
                </div>
                <ArrowRight className="w-4 h-4 text-[#6E7480]" />
              </Command.Item>
            </Command.Group>

            <Command.Group heading="Urgent Cases" className="text-xs font-mono font-semibold text-[#8A8F98] uppercase tracking-wider px-2 py-1.5 mt-2">
              <Command.Item
                onSelect={() => runCommand(() => router.push("/students/STU-001"))}
                className="flex items-center justify-between px-3 py-2.5 text-sm rounded-lg cursor-pointer hover:bg-white/[0.06] aria-selected:bg-white/[0.08] aria-selected:text-[#FFFFFF] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                  <span>Ananya Sharma (73.3%)</span>
                  <code className="text-xs font-mono text-[#8A8F98] bg-white/[0.04] px-1.5 py-0.5 rounded">BCREC-CS-2026-042</code>
                </div>
                <span className="text-xs font-mono text-[#A5AEF6] font-semibold">Review Plan</span>
              </Command.Item>

              <Command.Item
                onSelect={() => runCommand(() => router.push("/queue"))}
                className="flex items-center justify-between px-3 py-2.5 text-sm rounded-lg cursor-pointer hover:bg-white/[0.06] aria-selected:bg-white/[0.08] aria-selected:text-[#FFFFFF] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                  <span>Arjun Mehta (65.4%)</span>
                  <code className="text-xs font-mono text-[#8A8F98] bg-white/[0.04] px-1.5 py-0.5 rounded">BCREC-ME-2026-042</code>
                </div>
                <span className="text-xs font-mono text-rose-400 font-semibold">Escalated</span>
              </Command.Item>
            </Command.Group>
          </Command.List>

          <div className="px-4 py-2.5 border-t border-white/[0.08] bg-[#0E0F12] flex items-center justify-between text-xs text-[#6E7480] font-mono">
            <div className="flex items-center gap-4">
              <span>↑↓ Navigate</span>
              <span>↵ Select</span>
              <span>ESC Close</span>
            </div>
            <div className="flex items-center gap-1.5 text-[#8A8F98]">
              <Sparkles className="w-3.5 h-3.5 text-[#5E6AD2]" />
              <span>ASPIRE Command</span>
            </div>
          </div>
        </Command>
      </div>
    </div>
  );
}
