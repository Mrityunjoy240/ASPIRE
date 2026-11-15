"use client";

import React, { useState, useEffect } from "react";
import {
  Timer,
  Play,
  Pause,
  RotateCcw,
  Flame,
  Calendar,
  Sparkles,
  Quote,
  Coffee,
  CheckCircle2,
  Clock,
} from "lucide-react";

export function AestheticWidgets() {
  // ==========================================
  // 1. LIVE TIME & DATE
  // ==========================================
  const [timeStr, setTimeStr] = useState("10:00:00 AM");
  const [dateStr, setDateStr] = useState("Thursday, 14 Nov");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
      setDateStr(
        now.toLocaleDateString("en-US", {
          weekday: "short",
          day: "numeric",
          month: "short",
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // ==========================================
  // 2. POMODORO TIMER (25m / 5m / 15m)
  // ==========================================
  const [pomodoroMode, setPomodoroMode] = useState<"focus" | "short" | "long">("focus");
  const modeDurations = {
    focus: 25 * 60,
    short: 5 * 60,
    long: 15 * 60,
  };
  const [timeLeft, setTimeLeft] = useState(modeDurations.focus);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isRunning && timeLeft > 0) {
      timer = setInterval(() => {
        setTimeLeft((prev) => prev - 1);
      }, 1000);
    } else if (timeLeft === 0 && isRunning) {
      setIsRunning(false);
    }
    return () => clearInterval(timer);
  }, [isRunning, timeLeft]);

  const switchMode = (mode: "focus" | "short" | "long") => {
    setPomodoroMode(mode);
    setIsRunning(false);
    setTimeLeft(modeDurations[mode]);
  };

  const toggleTimer = () => setIsRunning(!isRunning);
  const resetTimer = () => {
    setIsRunning(false);
    setTimeLeft(modeDurations[pomodoroMode]);
  };

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Progress percentage of timer
  const timerProgress = Math.round(
    ((modeDurations[pomodoroMode] - timeLeft) / modeDurations[pomodoroMode]) * 100
  );

  // ==========================================
  // 3. DAILY QUOTE
  // ==========================================
  const quotes = [
    { quote: "Consistency over intensity.", author: "James Clear" },
    { quote: "30 minutes of daily recall beats 5 hours of panic cramming.", author: "Cognitive Science" },
    { quote: "Small disciplines repeated with consistency lead to great achievements.", author: "John C. Maxwell" },
  ];
  const [quoteIndex] = useState(0);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 select-none">
      {/* WIDGET 1: AESTHETIC POMODORO TIMER */}
      <div className="p-3.5 rounded-xl bg-[#191919] border border-white/[0.08] hover:border-white/[0.14] transition-all flex flex-col justify-between space-y-2.5 relative overflow-hidden">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs text-[#8A8F98]">
            <Timer className="w-3.5 h-3.5 text-[#e6ba7e]" />
            <span className="font-medium text-white/90">Focus Pomodoro</span>
          </div>
          <div className="flex items-center gap-1 bg-[#121212] p-0.5 rounded-md border border-white/[0.06]">
            <button
              onClick={() => switchMode("focus")}
              className={`px-1.5 py-0.5 text-[10px] font-mono rounded transition-colors ${
                pomodoroMode === "focus"
                  ? "bg-[#2A2A2A] text-white font-bold"
                  : "text-[#8A8F98] hover:text-white"
              }`}
            >
              25m
            </button>
            <button
              onClick={() => switchMode("short")}
              className={`px-1.5 py-0.5 text-[10px] font-mono rounded transition-colors ${
                pomodoroMode === "short"
                  ? "bg-[#2A2A2A] text-white font-bold"
                  : "text-[#8A8F98] hover:text-white"
              }`}
            >
              5m
            </button>
            <button
              onClick={() => switchMode("long")}
              className={`px-1.5 py-0.5 text-[10px] font-mono rounded transition-colors ${
                pomodoroMode === "long"
                  ? "bg-[#2A2A2A] text-white font-bold"
                  : "text-[#8A8F98] hover:text-white"
              }`}
            >
              15m
            </button>
          </div>
        </div>

        {/* Timer display */}
        <div className="flex items-center justify-between pt-1">
          <div>
            <div className="text-2xl font-bold font-mono text-white tracking-tight">
              {formatTimer(timeLeft)}
            </div>
            <span className="text-[10px] text-[#8A8F98] block">
              {isRunning ? "Session Active · Stay in Flow" : "Ready to Start"}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={toggleTimer}
              className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
                isRunning
                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30"
                  : "bg-white text-black font-semibold hover:bg-white/90"
              }`}
              title={isRunning ? "Pause Session" : "Start Focus Session"}
            >
              {isRunning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
            </button>
            <button
              onClick={resetTimer}
              className="w-7 h-7 rounded-lg bg-[#222222] border border-white/[0.08] text-[#8A8F98] hover:text-white hover:bg-white/[0.08] flex items-center justify-center transition-colors"
              title="Reset Timer"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full h-1 bg-white/[0.06] rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-amber-400 to-[#e6ba7e] transition-all duration-300"
            style={{ width: `${timerProgress}%` }}
          />
        </div>
      </div>

      {/* WIDGET 2: LIVE DIGITAL FLIP CLOCK & DATE */}
      <div className="p-3.5 rounded-xl bg-[#191919] border border-white/[0.08] hover:border-white/[0.14] transition-all flex flex-col justify-between space-y-2">
        <div className="flex items-center justify-between text-xs text-[#8A8F98]">
          <span className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-[#8fbce6]" />
            <span className="font-medium text-white/90">Local Time</span>
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/25">
            Durgapur, WB
          </span>
        </div>

        <div>
          <div className="text-xl font-bold font-mono text-white tracking-wide">
            {timeStr}
          </div>
          <div className="text-xs text-[#9d9b97] mt-0.5 font-medium flex items-center gap-1">
            <Calendar className="w-3 h-3 text-[#8A8F98]" />
            {dateStr} · Day 74 of Semester
          </div>
        </div>

        <div className="pt-1.5 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-[#8A8F98]">
          <span>Next Lecture:</span>
          <span className="text-white font-medium">10:00 AM (Room 302)</span>
        </div>
      </div>

      {/* WIDGET 3: STUDY STREAK & LOGGED HOURS */}
      <div className="p-3.5 rounded-xl bg-[#191919] border border-white/[0.08] hover:border-white/[0.14] transition-all flex flex-col justify-between space-y-2">
        <div className="flex items-center justify-between text-xs text-[#8A8F98]">
          <span className="flex items-center gap-1.5 font-medium text-white/90">
            <Flame className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
            Study Streak
          </span>
          <span className="text-[10px] font-mono text-amber-300 font-semibold">
            On Track 🔥
          </span>
        </div>

        <div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-bold font-mono text-white">3</span>
            <span className="text-xs text-[#8A8F98]">Days Active</span>
          </div>
          <p className="text-[11px] text-[#9d9b97] mt-0.5">
            2.5 hours studied today · Goal: 3.0h
          </p>
        </div>

        {/* 7-day dot trail */}
        <div className="pt-1.5 border-t border-white/[0.06] flex items-center justify-between">
          <span className="text-[10px] text-[#8A8F98]">This Week:</span>
          <div className="flex items-center gap-1">
            {["M", "T", "W", "T", "F", "S", "S"].map((day, i) => (
              <span
                key={i}
                className={`w-4 h-4 rounded text-[9px] font-mono flex items-center justify-center ${
                  i < 3
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold"
                    : i === 3
                    ? "bg-[#5E6AD2]/30 text-white border border-[#5E6AD2] font-bold"
                    : "bg-white/[0.04] text-[#6E7480]"
                }`}
                title={`Day ${day}`}
              >
                {day}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* WIDGET 4: SEMESTER 5 PROGRESS & AFFIRMATION */}
      <div className="p-3.5 rounded-xl bg-[#191919] border border-white/[0.08] hover:border-white/[0.14] transition-all flex flex-col justify-between space-y-2">
        <div className="flex items-center justify-between text-xs text-[#8A8F98]">
          <span className="flex items-center gap-1.5 font-medium text-white/90">
            <Sparkles className="w-3.5 h-3.5 text-[#b4a0e5]" />
            Semester 5
          </span>
          <span className="text-[10px] font-mono text-[#b4a0e5] font-semibold">
            68% Complete
          </span>
        </div>

        <div className="space-y-1.5">
          <div className="w-full h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-[#b4a0e5] rounded-full"
              style={{ width: "68%" }}
            />
          </div>
          <div className="flex items-center justify-between text-[11px] text-[#8A8F98]">
            <span>42 of 120 Days Left</span>
            <span className="font-mono text-white">ESE: Nov 23</span>
          </div>
        </div>

        <div className="pt-1.5 border-t border-white/[0.06]">
          <p className="text-[11px] text-[#9d9b97] italic line-clamp-1">
            "{quotes[quoteIndex].quote}"
          </p>
        </div>
      </div>
    </div>
  );
}

