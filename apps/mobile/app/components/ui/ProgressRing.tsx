"use client";

import React from "react";

interface ProgressRingProps {
  /** Percentage value (0-100) */
  progress: number;
  /** Size of the ring in pixels */
  size?: number;
  /** Stroke width */
  strokeWidth?: number;
  /** Color variant */
  variant?: "critical" | "warning" | "safe" | "default";
  /** Show percentage label in center */
  showLabel?: boolean;
  /** Custom className */
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
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colors.track}
          strokeWidth={strokeWidth}
          className="transition-all duration-500"
        />
        {/* Progress */}
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
          className="progress-ring__progress transition-all duration-700 ease-out"
          style={{ strokeDasharray: circumference, strokeDashoffset: offset }}
        />
      </svg>

      {showLabel && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-hero-stat text-white">
            {clampedProgress.toFixed(clampedProgress % 1 === 0 ? 0 : 1)}%
          </span>
        </div>
      )}
    </div>
  );
}