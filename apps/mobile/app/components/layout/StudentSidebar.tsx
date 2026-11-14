"use client";

import React from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  CalendarCheck,
  Sparkles,
  Milestone,
  BookOpen,
  GraduationCap,
  ChevronLeft,
  Flame,
} from "lucide-react";

interface StudentSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

interface NavSection {
  title?: string;
  items: {
    href: string;
    label: string;
    badge?: string;
    badgeVariant?: "rose" | "indigo" | "amber";
    icon: React.ComponentType<{ className?: string }>;
  }[];
}

const navSections: NavSection[] = [
  {
    title: "Daily Workspace",
    items: [
      {
        href: "/",
        label: "Command Center",
        icon: LayoutDashboard,
      },
      {
        href: "/attendance",
        label: "Attendance Ledger",
        badge: "73.3%",
        badgeVariant: "rose",
        icon: CalendarCheck,
      },
    ],
  },
  {
    title: "AI Learning Studio",
    items: [
      {
        href: "/study",
        label: "AI Study Corner",
        badge: "NotebookLM",
        badgeVariant: "indigo",
        icon: Sparkles,
      },
      {
        href: "/courses",
        label: "Courses & Notes",
        icon: BookOpen,
      },
    ],
  },
  {
    title: "Success & Recovery",
    items: [
      {
        href: "/plan",
        label: "My Recovery Plan",
        badge: "Active",
        badgeVariant: "amber",
        icon: Milestone,
      },
      {
        href: "/career",
        label: "Degree & Grades",
        icon: GraduationCap,
      },
    ],
  },
];

export function StudentSidebar({ collapsed, onToggle }: StudentSidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className={`
        fixed left-0 top-0 h-full z-40 border-r border-white/[0.08] bg-[#0D0E10]
        flex flex-col transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] select-none
        ${collapsed ? "w-16" : "w-64"}
      `}
      aria-label="Student sidebar navigation"
    >
      {/* Brand Header */}
      <div className="h-14 px-4 border-b border-white/[0.08] flex items-center justify-between">
        {!collapsed ? (
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-6 h-6 rounded-md bg-[#5E6AD2] flex items-center justify-center text-white shadow-sm transition-transform group-hover:scale-105">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2" />
              </svg>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm tracking-tight text-[#FFFFFF]">ASPIRE</span>
              <span className="text-[11px] text-[#8A8F98] font-mono px-1.5 py-0.5 rounded bg-white/[0.05] border border-white/[0.06]">
                STUDENT
              </span>
            </div>
          </Link>
        ) : (
          <div className="w-full flex justify-center">
            <div className="w-7 h-7 rounded-md bg-[#5E6AD2] flex items-center justify-center text-white shadow-sm">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2" />
              </svg>
            </div>
          </div>
        )}

        <button
          onClick={onToggle}
          className={`
            p-1.5 rounded-md text-[#8A8F98] hover:text-[#FFFFFF] hover:bg-white/[0.06] transition-colors
            ${collapsed ? "hidden" : "block"}
          `}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-label="Toggle sidebar"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5" role="navigation">
        {navSections.map((section, idx) => (
          <div key={idx} className="space-y-1">
            {!collapsed && section.title && (
              <div className="px-2.5 pb-1 text-xs font-semibold tracking-wider text-[#8A8F98] uppercase">
                {section.title}
              </div>
            )}
            {section.items.map((item) => {
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname === item.href || pathname.startsWith(item.href + "/");

              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={collapsed ? item.label : undefined}
                  className={`
                    group flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-120
                    ${
                      isActive
                        ? "bg-[#1C1D22] text-[#FFFFFF] border border-white/[0.10] shadow-sm"
                        : "text-[#9DA3AE] hover:text-[#FFFFFF] hover:bg-white/[0.04] border border-transparent"
                    }
                    ${collapsed ? "justify-center px-1.5" : ""}
                  `}
                >
                  <Icon
                    className={`w-4 h-4 shrink-0 transition-colors ${
                      isActive ? "text-[#5E6AD2]" : "text-[#8A8F98] group-hover:text-white"
                    }`}
                  />
                  {!collapsed && (
                    <>
                      <span className="truncate flex-1 text-[13px]">{item.label}</span>
                      {item.badge && (
                        <span
                          className={`
                            px-1.5 py-0.5 rounded text-[11px] font-mono font-medium border
                            ${
                              item.badgeVariant === "rose"
                                ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                                : item.badgeVariant === "indigo"
                                ? "bg-indigo-500/15 text-indigo-300 border-indigo-500/30"
                                : "bg-amber-500/15 text-amber-300 border-amber-500/30"
                            }
                          `}
                        >
                          {item.badge}
                        </span>
                      )}
                    </>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Student Profile Footer */}
      <div className="p-3 border-t border-white/[0.08] bg-[#0A0B0D]">
        {!collapsed ? (
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-xs font-mono font-bold text-indigo-300">
              AR
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-white truncate">Ananya Roy</p>
              <p className="text-[11px] text-[#8A8F98] font-mono truncate">BCREC/CSE/2024/042</p>
            </div>
            <div className="flex items-center gap-0.5 text-[11px] font-mono text-amber-300">
              <Flame className="w-3.5 h-3.5 text-amber-400" /> 3d
            </div>
          </div>
        ) : (
          <div className="w-full flex justify-center">
            <div className="w-7 h-7 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-[11px] font-mono font-bold text-indigo-300">
              AR
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
