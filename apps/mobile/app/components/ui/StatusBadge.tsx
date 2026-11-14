"use client";

import React from "react";

type StatusVariant = "critical" | "warning" | "safe" | "pending" | "overdue" | "pending-approval";

interface StatusBadgeProps {
  variant: StatusVariant;
  children: React.ReactNode;
  showPulse?: boolean;
  className?: string;
}

const variantStyles: Record<StatusVariant, { bg: string; text: string; border: string }> = {
  critical: { bg: "bg-rose-500/10", text: "text-rose-400", border: "border-rose-500/30" },
  overdue: { bg: "bg-rose-500/15", text: "text-rose-400", border: "border-rose-500/35" },
  warning: { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/30" },
  safe: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/30" },
  pending: { bg: "bg-sky-500/10", text: "text-sky-400", border: "border-sky-500/30" },
  "pending-approval": { bg: "bg-indigo-500/10", text: "text-indigo-400", border: "border-indigo-500/30" },
};

export function StatusBadge({
  variant,
  children,
  showPulse = false,
  className = "",
}: StatusBadgeProps) {
  const style = variantStyles[variant] || variantStyles.pending;

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 px-2 py-0.5 rounded
        text-[11px] font-mono font-medium border select-none
        ${style.bg} ${style.text} ${style.border} ${className}
      `}
    >
      {showPulse && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-current" />
        </span>
      )}
      {children}
    </span>
  );
}
