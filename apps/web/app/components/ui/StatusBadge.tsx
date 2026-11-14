"use client";

import React from "react";

type StatusVariant = "critical" | "warning" | "safe" | "pending" | "overdue" | "pending-approval";

interface StatusBadgeProps {
  variant: StatusVariant;
  children: React.ReactNode;
  showPulse?: boolean;
  className?: string;
}

const variantClasses = {
  critical: "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium border text-rose-400 bg-rose-500/15 border-rose-500/30",
  warning: "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium border text-amber-400 bg-amber-500/15 border-amber-500/30",
  safe: "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium border text-emerald-400 bg-emerald-500/15 border-emerald-500/30",
  pending: "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium border text-[#A5AEF6] bg-[#5E6AD2]/20 border-[#5E6AD2]/35",
  overdue: "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium border text-rose-300 bg-rose-600/25 border-rose-500/40",
  "pending-approval": "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium border text-[#A5AEF6] bg-[#5E6AD2]/20 border-[#5E6AD2]/35",
};

export function StatusBadge({
  variant,
  children,
  showPulse = true,
  className = "",
}: StatusBadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 ${variantClasses[variant]} ${className}`}>
      {showPulse && (variant === "critical" || variant === "overdue") && (
        <span className="w-1 h-1 rounded-full bg-current" aria-hidden="true" />
      )}
      {children}
    </span>
  );
}
