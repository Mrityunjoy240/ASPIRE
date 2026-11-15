"use client";

import React from "react";

interface CardProps {
  children: React.ReactNode;
  elevated?: boolean;
  className?: string;
  [key: string]: React.ReactNode | boolean | string | undefined;
}

export function Card({ children, elevated = false, className = "", ...props }: CardProps) {
  return (
    <div
      className={`rounded-lg border transition-all duration-150 ${
        elevated
          ? "border-white/[0.12] bg-[#16171A] p-5 shadow-lg shadow-black/40"
          : "border-white/[0.08] bg-[#121316] p-4.5 hover:border-white/[0.15]"
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
