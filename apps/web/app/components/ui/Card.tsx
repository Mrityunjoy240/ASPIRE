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
      className={`rounded-xl border transition-all duration-200 ${
        elevated
          ? "border-white/[0.12] bg-[#151E32]/80 backdrop-blur-xl p-6 shadow-xl shadow-black/30"
          : "border-white/[0.08] bg-[#0E1422]/80 backdrop-blur-xl p-5 shadow-lg shadow-black/20 hover:border-white/[0.15]"
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}