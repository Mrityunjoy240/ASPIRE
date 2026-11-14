"use client";

import React from "react";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-[#5E6AD2] hover:bg-[#6875E3] text-[#FFFFFF] font-medium shadow-sm border border-indigo-400/20 active:scale-[0.98]",
  secondary:
    "bg-white/[0.05] hover:bg-white/[0.08] text-[#ECEEF0] border border-white/[0.08] active:scale-[0.98]",
  danger:
    "bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/25 active:scale-[0.98]",
  ghost:
    "bg-transparent hover:bg-white/[0.05] text-[#9DA3AE] hover:text-[#FFFFFF] border border-transparent active:scale-[0.98]",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-7 px-2.5 text-xs rounded-md",
  md: "h-8 px-3 text-[13px] rounded-md",
  lg: "h-9 px-4 text-sm rounded-md",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  iconPosition = "left",
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      className={`
        inline-flex items-center justify-center gap-1.5 font-medium
        transition-all duration-120 select-none
        disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none
        ${variantClasses[variant]} ${sizeClasses[size]} ${className}
      `}
      disabled={isDisabled}
      {...props}
    >
      {loading ? (
        <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" aria-hidden="true">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : icon && iconPosition === "left" ? (
        <span aria-hidden="true" className="shrink-0">{icon}</span>
      ) : null}
      {children}
      {icon && iconPosition === "right" && !loading && (
        <span aria-hidden="true" className="shrink-0">{icon}</span>
      )}
    </button>
  );
}
