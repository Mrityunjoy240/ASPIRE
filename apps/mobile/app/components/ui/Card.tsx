"use client";

import React from "react";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  elevated?: boolean;
  className?: string;
}

export function Card({ children, elevated = false, className = "", ...props }: CardProps) {
  return (
    <div
      className={`
        rounded-lg border transition-all duration-150
        ${
          elevated
            ? "bg-[#121316] border-white/[0.12] shadow-xl shadow-black/40"
            : "bg-[#0D0E10] border-white/[0.08] shadow-sm hover:border-white/[0.14]"
        }
        ${className}
      `}
      {...props}
    >
      {children}
    </div>
  );
}
