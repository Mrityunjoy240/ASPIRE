"use client";

import React from "react";

interface ProgressRingProps {
  progress: number;
  size?: number;
  strokeWidth?: number;
  variant?: "critical" | "warning" | "safe" | "default";
  showLabel?: boolean;
  className?: string;
}

const variantColors = {
  critical: { progress: "#F43F5E", track: "rgba(244, 63, 94, 0.15)" },
  warning: { progress: "#F59E0B", track: "rgba(245, 158, 11, 0.15)" },
  safe: { progress: "#10B981", track: "rgba(16, 185, 129, 0.15)" },
  default: { progress: "#6366F1", track: "rgba(99, 102, 241, 0.15)" },
};

export function ProgressRing({
  progress = 0,
  size = 120,
  strokeWidth = 8,
  variant = "default",
  showLabel = true,
  className = "",
}: ProgressRingProps) {
  const clampedProgress = Math.max(0, Math.min(100, progress));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clampedProgress / 100);
  const colors = variantColors[variant];

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colors.track}
          strokeWidth={strokeWidth}
          className="transition-all duration-500"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colors.progress}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
          style={{ strokeDasharray: circumference, strokeDashoffset: offset }}
        />
      </svg>

      {showLabel && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className="font-mono font-bold text-white"
            style={{ fontSize: Math.max(9, Math.round(size / 5)) }}
          >
            {clampedProgress.toFixed(clampedProgress % 1 === 0 ? 0 : 1)}%
          </span>
        </div>
      )}
    </div>
  );
}
