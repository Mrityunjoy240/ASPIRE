"use client";

import React from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  Compass,
  CalendarCheck,
  Sparkles,
  Milestone,
} from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  badge?: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  {
    href: "/",
    label: "Today",
    icon: Compass,
  },
  {
    href: "/attendance",
    label: "Attendance",
    badge: "73%",
    icon: CalendarCheck,
  },
  {
    href: "/study",
    label: "Study Corner",
    badge: "AI",
    icon: Sparkles,
  },
  {
    href: "/plan",
    label: "My Plan",
    badge: "Active",
    icon: Milestone,
  },
];

export function BottomNavigation() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-white/[0.08] bg-[#0D0E10]/95 backdrop-blur-md"
      role="navigation"
      aria-label="Student main navigation"
    >
      <div className="max-w-lg mx-auto flex items-center justify-around h-14 px-3">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname === item.href || pathname.startsWith(item.href + "/");

          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                relative flex flex-col items-center justify-center py-1 px-3 rounded-md transition-all duration-120
                ${
                  isActive
                    ? "text-[#FFFFFF] bg-white/[0.06]"
                    : "text-[#8A8F98] hover:text-[#FFFFFF] hover:bg-white/[0.03]"
                }
              `}
              aria-current={isActive ? "page" : undefined}
            >
              <div className="relative">
                <Icon className={`w-4 h-4 ${isActive ? "text-[#5E6AD2]" : "text-[#8A8F98]"}`} />
                {item.badge && (
                  <span
                    className={`
                      absolute -top-1.5 -right-3 text-[9px] font-mono font-semibold px-1 rounded-full
                      ${
                        item.badge === "73%"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                          : "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                      }
                    `}
                  >
                    {item.badge}
                  </span>
                )}
              </div>
              <span className="text-[11px] font-medium tracking-tight mt-1">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
