"use client";

import React from "react";

type StatusVariant = "critical" | "warning" | "safe" | "pending" | "overdue" | "pending-approval";

interface StatusBadgeProps {
  variant: StatusVariant;
  children: React.ReactNode;
  /** Show pulsing dot for critical/overdue */
  showPulse?: boolean;
  /** Custom className */
  className?: string;
}

const variantClasses = {
  critical: "badge-critical",
  warning: "badge-warning",
  safe: "badge-safe",
  pending: "badge-pending",
  overdue: "badge-overdue",
  "pending-approval": "badge-pending-approval",
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