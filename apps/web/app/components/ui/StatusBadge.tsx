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
  critical: "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold font-mono border text-rose-400 bg-rose-500/10 border-rose-500/30",
  warning: "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold font-mono border text-amber-400 bg-amber-500/10 border-amber-500/30",
  safe: "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold font-mono border text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  pending: "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold font-mono border text-sky-400 bg-sky-500/10 border-sky-500/30",
  overdue: "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold font-mono border animate-pulse text-rose-300 bg-rose-600/20 border-rose-500/40",
  "pending-approval": "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold font-mono border text-sky-400 bg-sky-500/10 border-sky-500/30",
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
        <span className="w-1.5 h-1.5 rounded-full bg-current animate-ping" aria-hidden="true" />
      )}
      {children}
    </span>
  );
}