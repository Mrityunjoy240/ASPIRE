"use client";

import React from "react";

type ButtonVariant = "primary" | "secondary" | "accent" | "danger" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-[#FFFFFF] hover:bg-white/90 text-[#08090A] font-medium shadow-sm",
  secondary: "bg-white/[0.04] hover:bg-white/[0.08] text-[#D1D5DB] hover:text-white border border-white/[0.08]",
  accent: "bg-[#5E6AD2] hover:bg-[#6875E3] text-white font-medium",
  danger: "bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30",
  ghost: "bg-transparent hover:bg-white/[0.05] text-[#8A8F98] hover:text-[#F7F8F8]",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-7 px-2.5 text-xs rounded",
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
        inline-flex items-center justify-center gap-2 font-medium
        active:scale-[0.98] transition-all duration-150
        disabled:opacity-50 disabled:cursor-not-allowed
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
        <span aria-hidden="true">{icon}</span>
      ) : null}
      {children}
      {icon && iconPosition === "right" && !loading && <span aria-hidden="true">{icon}</span>}
    </button>
  );
}
