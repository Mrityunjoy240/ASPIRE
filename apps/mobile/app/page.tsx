"use client";

import React, { useState } from "react";
import { MobileLayout } from "@/components/MobileLayout";
import { ProgressRing } from "@/components/ui/ProgressRing";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Slider } from "@/components/ui/Slider";

const MOCK_ATTENDANCE = {
  current: 73.3,
  conducted: 30,
  attended: 22,
  threshold: 75,
  requiredToRecover: 3,
  projected: 75.8,
};

const MOCK_PLAN = {
  id: "CAS-BCREC-2026-0042",
  title: "DBMS Attendance Recovery Plan",
  urgency: "critical" as const,
  evidence: [
    "Attendance: 73.3% (22/30 classes)",
    "Threshold: 75.0% (Institutional rule)",
    "Exam in 8 days",
    "Declining trend: -2.1% last week",
  ],
  actions: [
    { type: "ATTEND_CLASS", subject: "DBMS", target: 3, desc: "Attend next 3 consecutive classes" },
    { type: "STUDY_BLOCK", subject: "DBMS Unit 3", duration: 45, desc: "Normalization & 3NF practice" },
    { type: "PRACTICE_QUIZ", subject: "DBMS", source: "uploaded notes", desc: "10-question checkpoint quiz" },
  ],
  confidence: "HIGH",
};

export default function OverviewPage() {
  const [sliderValue, setSliderValue] = useState(0);
  const [projectedPct, setProjectedPct] = useState(MOCK_ATTENDANCE.current);

  // Calculate projected attendance based on slider
  const handleSliderChange = (value: number) => {
    setSliderValue(value);
    const attended = MOCK_ATTENDANCE.attended + value;
    const conducted = MOCK_ATTENDANCE.conducted + value;
    const pct = (attended / conducted) * 100;
    setProjectedPct(pct);
  };

  const isRecovered = projectedPct >= MOCK_ATTENDANCE.threshold;
  const requiredMore = isRecovered ? 0 : MOCK_ATTENDANCE.requiredToRecover - sliderValue;

  return (
    <MobileLayout>
      <div className="p-4 space-y-4 animate-slide-up">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-page-title">Good morning, Ananya</h1>
            <p className="text-body">Here's what needs your attention today</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-micro">DBMS · Sem 5</span>
          </div>
        </header>

        {/* Hero Attendance Risk Card */}
        <Card className="relative overflow-hidden">
          <div className="flex flex-col md:flex-row items-center md:items-start justify-between gap-6">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-4">
                <StatusBadge variant="critical" showPulse>
                  CRITICAL RISK
                </StatusBadge>
                <span className="text-micro text-slate-500">DBMS · Semester 5</span>
              </div>
              <p className="text-body text-slate-400 mb-4">
                Your attendance is <span className="text-rose-400 font-semibold">2.7%</span> below the
                <span className="font-mono font-semibold">75.0%</span> institutional threshold.
              </p>

              {/* What-If Calculator */}
              <div className="space-y-3 p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-section-heading text-xs">What-If Calculator</span>
                  <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded-full ${
                    isRecovered ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
                    : "text-rose-400 bg-rose-500/10 border-rose-500/30"
                  }`}>
                    {isRecovered ? "RECOVERED ✓" : `${requiredMore} more class${requiredMore !== 1 ? "es" : ""} needed`}
                  </span>
                </div>
                <p className="text-body text-slate-400 mb-3">
                  Slide to see how many classes you need to attend to reach <span className="font-mono font-semibold text-indigo-400">75.0%</span>
                </p>
                <Slider
                  value={sliderValue}
                  min={0}
                  max={MOCK_ATTENDANCE.requiredToRecover}
                  step={1}
                  onChange={handleSliderChange}
                  formatValue={(v) => `Attend next ${v} class${v !== 1 ? "es" : ""}`}
                  showValue={true}
                />
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400">Current: {MOCK_ATTENDANCE.current.toFixed(1)}%</span>
                  <span className={`font-mono font-semibold ${isRecovered ? "text-emerald-400" : "text-rose-400"}`}>
                    Projected: {projectedPct.toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Recovery Math Display */}
              <div className="mt-4 grid grid-cols-3 gap-3 text-center">
                <div className="p-3 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                  <div className="text-2xl font-extrabold font-mono text-white">{MOCK_ATTENDANCE.attended + sliderValue}</div>
                  <div className="text-micro text-slate-500">Attended</div>
                </div>
                <div className="p-3 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                  <div className="text-2xl font-extrabold font-mono text-white">{MOCK_ATTENDANCE.conducted + sliderValue}</div>
                  <div className="text-micro text-slate-500">Conducted</div>
                </div>
                <div className="p-3 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                  <div className="text-2xl font-extrabold font-mono" style={{ color: isRecovered ? "#10B981" : "#F43F5E" }}>
                    {projectedPct.toFixed(1)}%
                  </div>
                  <div className="text-micro text-slate-500">Projected</div>
                </div>
              </div>
            </div>

            {/* Progress Ring */}
            <div className="flex-shrink-0">
              <ProgressRing
                progress={projectedPct}
                size={140}
                strokeWidth={10}
                variant={projectedPct >= MOCK_ATTENDANCE.threshold ? "safe" : "critical"}
                showLabel
              />
            </div>
          </div>

          {/* Threshold marker */}
          <div className="absolute bottom-4 right-4 md:bottom-6 md:right-8 flex items-center gap-2">
            <div className="w-24 h-px bg-gradient-to-r from-transparent via-rose-500/50 to-transparent" />
            <span className="text-xs font-mono text-rose-400/80 whitespace-nowrap">Threshold 75.0%</span>
          </div>
        </Card>

        {/* Pending Intervention Action Banner */}
        <Card className="border-critical/30 bg-rose-500/5 backdrop-blur-xl">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" aria-hidden="true" />
                <span className="text-section-heading text-rose-400">Intervention Plan Pending</span>
                <StatusBadge variant="pending-approval">AWAITING YOUR DECISION</StatusBadge>
              </div>
              <p className="text-body text-slate-300 mb-2">
                Your mentor has proposed a recovery plan for DBMS attendance risk.
                <span className="font-mono text-rose-400"> Case #{MOCK_PLAN.id} </span>
              </p>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="primary" onClick={() => console.log("Accept plan")}>
                  Accept Plan
                </Button>
                <Button size="sm" variant="danger" onClick={() => console.log("Decline plan")}>
                  Decline
                </Button>
                <Button size="sm" variant="ghost" onClick={() => console.log("View details")}>
                  View Details
                </Button>
              </div>
            </div>
            <div className="flex-shrink-0">
              <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-rose-500/20 to-rose-600/10 flex items-center justify-center border border-rose-500/30">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-rose-400">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
              </div>
            </div>
          </div>
        </Card>

        {/* Quick Stats Row */}
        <div className="grid grid-cols-2 gap-3">
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-section-heading">Next Task</div>
                <div className="text-body mt-1">Submit Math Assignment 2</div>
                <div className="text-micro text-slate-500 mt-1">Due tomorrow · 45 min</div>
              </div>
              <div className="w-12 h-12 rounded-xl bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-indigo-400">
                  <path d="M9 11l3 3L22 4" />
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                </svg>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-section-heading">Exam Countdown</div>
                <div className="text-hero-stat text-indigo-400 font-mono mt-1">8 days</div>
                <div className="text-micro text-slate-500 mt-1">DBMS ESE</div>
              </div>
              <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center border border-amber-500/30">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-amber-400">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </MobileLayout>
  );
}