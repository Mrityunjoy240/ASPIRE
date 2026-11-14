"use client";

import React from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  Inbox,
  BarChart3,
  Users,
  Building2,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

interface NavSection {
  title?: string;
  items: {
    href: string;
    label: string;
    badge?: string;
    badgeVariant?: "rose" | "accent";
    icon: React.ComponentType<{ className?: string }>;
  }[];
}

const navSections: NavSection[] = [
  {
    title: "Workspace",
    items: [
      {
        href: "/",
        label: "Command Center",
        icon: LayoutDashboard,
      },
    ],
  },
  {
    title: "Intelligence",
    items: [
      {
        href: "/queue",
        label: "Triage Queue",
        badge: "10",
        badgeVariant: "rose",
        icon: Inbox,
      },
      {
        href: "/analytics",
        label: "Risk Analytics",
        icon: BarChart3,
      },
    ],
  },
  {
    title: "Operations",
    items: [
      {
        href: "/students",
        label: "Student Directory",
        badge: "247",
        badgeVariant: "accent",
        icon: Users,
      },
      {
        href: "/admin/institutions",
        label: "Institutions & Rules",
        icon: Building2,
      },
    ],
  },
];

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className={`
        fixed left-0 top-0 h-full z-40 border-r border-white/[0.08] bg-[#0D0E10]
        flex flex-col transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] select-none
        ${collapsed ? "w-16" : "w-64"}
      `}
      aria-label="Sidebar navigation"
    >
      {/* Brand Header — Aligned exactly with Topbar h-14 */}
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
              <span className="text-xs text-[#8A8F98] font-mono px-1.5 py-0.5 rounded bg-white/[0.05] border border-white/[0.06]">
                v1.0
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
                    className={`w-4 h-4 flex-shrink-0 transition-transform group-hover:scale-110 ${
                      isActive ? "text-[#FFFFFF]" : "text-[#8A8F98] group-hover:text-[#FFFFFF]"
                    }`}
                  />
                  {!collapsed && <span className="truncate">{item.label}</span>}

                  {!collapsed && item.badge && (
                    <span
                      className={`
                        ml-auto px-2 py-0.5 rounded-full text-xs font-mono font-semibold transition-transform group-hover:scale-105
                        ${
                          item.badgeVariant === "rose"
                            ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                            : "bg-[#5E6AD2]/20 text-[#A5AEF6] border border-[#5E6AD2]/30"
                        }
                      `}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer Institution info */}
      <div className="p-3 border-t border-white/[0.08] bg-[#08090A]">
        {!collapsed ? (
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-[#121316] border border-white/[0.07]">
            <div className="w-7 h-7 rounded-md bg-white/[0.08] flex items-center justify-center text-xs font-mono font-bold text-white">
              B
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-[#FFFFFF] truncate leading-tight">BCREC Durgapur</p>
              <p className="text-xs text-[#8A8F98] font-mono truncate">Reference College</p>
            </div>
            <span className="w-2 h-2 rounded-full bg-emerald-400 linear-pulse-dot" />
          </div>
        ) : (
          <button
            onClick={onToggle}
            className="w-full py-1.5 flex justify-center text-[#8A8F98] hover:text-[#FFFFFF]"
            title="Expand sidebar"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        )}
      </div>
    </aside>
  );
}
