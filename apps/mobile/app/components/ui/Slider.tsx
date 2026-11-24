"use client";

import React, { useRef, useEffect, useState } from "react";

interface SliderProps {
  /** Current value */
  value: number;
  /** Minimum value */
  min?: number;
  /** Maximum value */
  max?: number;
  /** Step increment */
  step?: number;
  /** Callback when value changes */
  onChange: (value: number) => void;
  /** Show value label */
  showValue?: boolean;
  /** Value formatter */
  formatValue?: (value: number) => string;
  /** Custom className */
  className?: string;
  /** Disabled state */
  disabled?: boolean;
}

export function Slider({
  value,
  min = 0,
  max = 10,
  step = 1,
  onChange,
  showValue = true,
  formatValue,
  className = "",
  disabled = false,
}: SliderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);
  const thumbRef = useRef<HTMLDivElement>(null);

  const percentage = ((value - min) / (max - min)) * 100;

  const handlePointerDown = (e: React.PointerEvent | React.TouchEvent) => {
    if (disabled) return;
    setIsDragging(true);
    updateValueFromEvent(e);
  };

  const handlePointerMove = (e: React.PointerEvent | React.TouchEvent | PointerEvent | TouchEvent) => {
    if (!isDragging || disabled) return;
    updateValueFromEvent(e);
  };

  const handlePointerUp = () => {
    setIsDragging(false);
  };

  const updateValueFromEvent = (e: React.PointerEvent | React.TouchEvent | PointerEvent | TouchEvent) => {
    if (!trackRef.current) return;
    const rect = trackRef.current.getBoundingClientRect();
    const clientX = "touches" in e ? e.touches[0].clientX : e.clientX;
    const relativeX = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const newValue = Math.round((relativeX * (max - min) + min) / step) * step;
    onChange(Math.max(min, Math.min(max, newValue)));
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener("pointermove", handlePointerMove);
      window.addEventListener("pointerup", handlePointerUp);
      window.addEventListener("touchmove", handlePointerMove, { passive: true });
      window.addEventListener("touchend", handlePointerUp);
    }
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("touchmove", handlePointerMove);
      window.removeEventListener("touchend", handlePointerUp);
    };
  }, [isDragging]);

  return (
    <div className={`relative ${className}`} style={{ touchAction: "none" }}>
      <div
        ref={trackRef}
        className="relative h-2 bg-white/[0.08] rounded-full overflow-hidden"
        onPointerDown={handlePointerDown}
        onTouchStart={handlePointerDown}
        style={{ cursor: disabled ? "not-allowed" : "pointer" }}
      >
        {/* Filled track */}
        <div
          className="absolute top-0 bottom-0 left-0 rounded-full bg-gradient-to-r from-indigo-500 to-indigo-400"
          style={{ width: `${percentage}%` }}
        />
        {/* Target marker at 75% */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-0.5 h-4 bg-white/50"
          style={{ left: "75%" }}
          aria-hidden="true"
        />
        {/* Thumb */}
        <div
          ref={thumbRef}
          className={`
            absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-6 rounded-full
            bg-gradient-to-br from-indigo-400 to-indigo-600 border-2 border-white/20
            shadow-lg shadow-indigo-500/25 transition-all duration-200
            ${isDragging ? "scale-125" : ""}
            ${disabled ? "opacity-50 cursor-not-allowed" : "hover:scale-110"}
          `}
          style={{ left: `${percentage}%` }}
          aria-label={`Attendance projection: ${formatValue ? formatValue(value) : value}`}
          role="slider"
          aria-valuemin={min}
          aria-valuemax={max}
          aria-valuenow={value}
          tabIndex={disabled ? -1 : 0}
          onKeyDown={(e) => {
            if (disabled) return;
            let newValue = value;
            if (e.key === "ArrowRight" || e.key === "ArrowUp") newValue = Math.min(max, value + step);
            if (e.key === "ArrowLeft" || e.key === "ArrowDown") newValue = Math.max(min, value - step);
            if (newValue !== value) onChange(newValue);
          }}
        />
      </div>

      {showValue && (
        <div className="mt-3 flex items-center justify-between text-sm">
          <span className="text-slate-400">Current: {formatValue ? formatValue(value) : value}</span>
          <span className="text-indigo-400 font-mono font-semibold">
            {formatValue ? formatValue(value) : value}
          </span>
        </div>
      )}
    </div>
  );
}