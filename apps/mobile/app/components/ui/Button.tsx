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
  primary: "bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white font-medium shadow-lg shadow-indigo-500/25",
  secondary: "bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 border border-white/[0.08]",
  danger: "bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30",
  ghost: "bg-transparent hover:bg-white/[0.05] text-slate-300",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm rounded-lg",
  md: "px-4 py-2.5 text-sm rounded-lg",
  lg: "px-6 py-3 text-base rounded-xl",
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
        inline-flex items-center justify-center gap-2 font-medium rounded-lg
        active:scale-[0.98] transition-all duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantClasses[variant]} ${sizeClasses[size]} ${className}
      `}
      disabled={isDisabled}
      {...props}
    >
      {loading ? (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
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