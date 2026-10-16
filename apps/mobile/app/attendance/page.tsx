"use client";

import React from "react";
import { MobileLayout } from "@/components/MobileLayout";
import { ProgressRing } from "@/components/ui/ProgressRing";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Card } from "@/components/ui/Card";
import { Slider } from "@/components/ui/Slider";

const COURSES = [
  {
    id: "cs501",
    name: "Database Management Systems",
    code: "CS501",
    conducted: 30,
    attended: 22,
    threshold: 75,
    trend: "declining" as const,
  },
  {
    id: "cs502",
    name: "Computer Networks",
    code: "CS502",
    conducted: 28,
    attended: 24,
    threshold: 75,
    trend: "stable" as const,
  },
  {
    id: "cs503",
    name: "Operating Systems",
    code: "CS503",
    conducted: 26,
    attended: 17,
    threshold: 75,
    trend: "critical" as const,
  },
];

function calculatePercentage(attended: number, conducted: number) {
  return conducted > 0 ? ((attended / conducted) * 100).toFixed(1) : "0.0";
}

function getTrendLabel(trend: string) {
  switch (trend) {
    case "declining": return "Declining";
    case "critical": return "Critical";
    default: return "Stable";
  }
}

export default function AttendancePage() {
  return (
    <MobileLayout>
      <div className="p-4 space-y-4 animate-slide-up">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-page-title">Attendance</h1>
            <p className="text-body">Track your attendance across all courses</p>
          </div>
        </header>

        {/* Aggregate Summary */}
        <Card className="relative overflow-hidden">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-4">
                <StatusBadge variant="critical" showPulse>
                  AGGREGATE: CRITICAL RISK
                </StatusBadge>
              </div>
              <p className="text-body text-slate-400 mb-4">
                Overall attendance across all courses. Minimum threshold: <span className="font-mono font-semibold">75.0%</span>
              </p>

              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-3 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                  <div className="text-2xl font-extrabold font-mono text-white">68</div>
                  <div className="text-micro text-slate-500">Total Classes</div>
                </div>
                <div className="p-3 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                  <div className="text-2xl font-extrabold font-mono text-white">49</div>
                  <div className="text-micro text-slate-500">Attended</div>
                </div>
                <div className="p-3 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                  <div className="text-2xl font-extrabold font-mono text-rose-400">72.1%</div>
                  <div className="text-micro text-slate-500">Aggregate</div>
                </div>
              </div>
            </div>
            <ProgressRing
              progress={72.1}
              size={120}
              strokeWidth={10}
              variant="critical"
              showLabel
            />
          </div>
        </Card>

        {/* Course List */}
        <div className="space-y-3">
          <h2 className="text-section-heading">Course Breakdown</h2>
          {COURSES.map((course) => {
            const pct = parseFloat(calculatePercentage(course.attended, course.conducted));
            const variant: "safe" | "warning" | "critical" = pct >= course.threshold ? "safe" : pct >= course.threshold - 5 ? "warning" : "critical";
            const required = Math.ceil((course.threshold / 100 * (course.conducted + course.attended) - course.attended) / (1 - course.threshold / 100));

            return (
              <Card key={course.id} className="group">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <div>
                        <h3 className="font-semibold text-white truncate">{course.name}</h3>
                        <div className="text-micro text-slate-500">{course.code} · Semester 5</div>
                      </div>
                      <StatusBadge variant={variant} showPulse={variant === "critical"}>
                        {getTrendLabel(course.trend)} ({calculatePercentage(course.attended, course.conducted)}%)
                      </StatusBadge>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-slate-400 mb-3">
                      <span className="flex items-center gap-1">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-slate-500">
                          <rect x="3" y="4" width="18" height="18" rx="2" />
                          <line x1="16" y1="2" x2="16" y2="6" />
                          <line x1="8" y1="2" x2="8" y2="6" />
                          <line x1="3" y1="10" x2="21" y2="10" />
                        </svg>
                        {course.attended}/{course.conducted} classes
                      </span>
                      <span className="flex items-center gap-1">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-slate-500">
                          <circle cx="12" cy="12" r="10" />
                          <polyline points="12 6 12 12 16 14" />
                        </svg>
                        Threshold {course.threshold}%
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-slate-500">Classes needed to recover:</span>
                      <span className="font-mono font-semibold text-rose-400">{required > 0 ? required : 0}</span>
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    <ProgressRing
                      progress={parseFloat(calculatePercentage(course.attended, course.conducted))}
                      size={80}
                      strokeWidth={6}
                      variant={variant}
                      showLabel
                    />
                  </div>
                </div>
              </Card>
            );
          })}
        </div>

        {/* What-If Calculator Section */}
        <Card className="border-indigo-500/20 bg-indigo-500/5">
          <h3 className="text-section-heading mb-4 flex items-center gap-2">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-indigo-400">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
            What-If Calculator
          </h3>
          <p className="text-body text-slate-400 mb-4">
            Slide to see how many classes you need to attend in <span className="font-mono font-semibold text-indigo-400">DBMS</span> to reach the 75% threshold.
          </p>
          <Slider
            value={0}
            min={0}
            max={5}
            step={1}
            onChange={(v) => console.log(v)}
            formatValue={(v) => `Attend next ${v} class${v !== 1 ? "es" : ""}`}
            showValue={true}
          />
          <div className="mt-4 p-3 bg-white/[0.03] rounded-xl border border-white/[0.04]">
            <div className="text-body text-slate-400 mb-2">
              <strong className="text-white">Formula:</strong> (Attended + X) / (Conducted + X) ≥ 0.75
            </div>
            <div className="font-mono text-indigo-400 text-sm">
              X ≥ {(0.75 * 30 - 22) / (1 - 0.75)}
            </div>
            <div className="text-rose-400 text-sm mt-1">
              Minimum 3 consecutive classes required to reach 75%
            </div>
          </div>
        </Card>

        {/* Legend */}
        <div className="flex flex-wrap gap-2">
          <StatusBadge variant="critical">Critical Risk (&lt;75%)</StatusBadge>
          <StatusBadge variant="warning">Warning (75-80%)</StatusBadge>
          <StatusBadge variant="safe">Safe (&gt;80%)</StatusBadge>
        </div>
      </div>
    </MobileLayout>
  );
}