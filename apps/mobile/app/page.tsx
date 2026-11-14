"use client";

import React, { useState } from "react";
import Link from "next/link";
import { MobileLayout } from "@/components/MobileLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  Clock,
  CheckCircle2,
  Calendar,
  Sparkles,
  ChevronRight,
  Flame,
} from "lucide-react";

interface ScheduleItem {
  id: string;
  time: string;
  subject: string;
  code: string;
  room: string;
  faculty: string;
  type: "lecture" | "lab";
  status: "upcoming" | "in-progress" | "completed";
}

const TODAY_SCHEDULE: ScheduleItem[] = [
  {
    id: "s1",
    time: "10:00 - 11:00 AM",
    subject: "Database Management Systems",
    code: "CS501",
    room: "Room 302",
    faculty: "Prof. Raj Kumar Samanta",
    type: "lecture",
    status: "upcoming",
  },
  {
    id: "s2",
    time: "11:30 - 12:30 PM",
    subject: "Operating Systems",
    code: "CS502",
    room: "Room 204",
    faculty: "Dr. Anirban Bose",
    type: "lecture",
    status: "upcoming",
  },
  {
    id: "s3",
    time: "02:00 - 04:30 PM",
    subject: "DBMS Laboratory",
    code: "CS591",
    room: "Software Lab 3",
    faculty: "Prof. Joyjit Patra",
    type: "lab",
    status: "upcoming",
  },
];

const SUBJECTS_VITALS = [
  { code: "CS501", name: "DBMS", current: 73.3, threshold: 75, safeBunks: 0, status: "critical" as const },
  { code: "CS502", name: "Operating Systems", current: 82.1, threshold: 75, safeBunks: 2, status: "safe" as const },
  { code: "CS503", name: "Computer Networks", current: 78.6, threshold: 75, safeBunks: 1, status: "safe" as const },
  { code: "CS504", name: "AI & ML", current: 88.0, threshold: 75, safeBunks: 4, status: "safe" as const },
];

export default function StudentHomePage() {
  const [sliderValue, setSliderValue] = useState(0);

  // Deterministic What-If Calculation
  const attendedInitial = 22;
  const conductedInitial = 30;
  const threshold = 75.0;

  const attendedProjected = attendedInitial + sliderValue;
  const conductedProjected = conductedInitial + sliderValue;
  const projectedPct = ((attendedProjected / conductedProjected) * 100);
  const isRecovered = projectedPct >= threshold;
  const classesNeeded = isRecovered ? 0 : Math.max(0, 3 - sliderValue);

  return (
    <MobileLayout>
      <div className="space-y-4">
        {/* Welcome Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-white tracking-tight">Good morning, Ananya</h1>
              <span className="flex items-center gap-1 text-[11px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/25">
                <Flame className="w-3 h-3 text-amber-400" /> 3-Day Streak
              </span>
            </div>
            <p className="text-xs text-[#8A8F98]">
              Roll: <span className="font-mono text-white/80">BCREC/CSE/2024/042</span> · Section A
            </p>
          </div>
          <Link href="/plan">
            <Button size="sm" variant="secondary" icon={<Sparkles className="w-3.5 h-3.5 text-[#5E6AD2]" />}>
              Active Plan
            </Button>
          </Link>
        </div>

        {/* Hero Critical Attendance Risk Card with What-If Simulator */}
        <Card className="p-4 border-rose-500/30 bg-gradient-to-b from-[#121014] to-[#0D0E10] relative overflow-hidden">
          <div className="absolute top-0 right-0 w-36 h-36 bg-rose-500/[0.04] rounded-full blur-2xl pointer-events-none" />

          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              <StatusBadge variant="critical" showPulse>
                CRITICAL RISK
              </StatusBadge>
              <span className="text-xs font-semibold text-white">CS501 · DBMS</span>
            </div>
            <span className="text-[11px] font-mono text-rose-300 bg-rose-500/15 border border-rose-500/30 px-2 py-0.5 rounded">
              Exam in 8 Days
            </span>
          </div>

          <p className="text-xs text-[#ECEEF0] leading-relaxed mb-3">
            Your current attendance is <span className="text-rose-400 font-mono font-bold">73.3%</span> (22/30 classes), which is below BCREC's mandatory <span className="font-mono font-semibold text-white">75.0%</span> threshold.
          </p>

          {/* What-If Simulator Box */}
          <div className="bg-[#121316] border border-white/[0.08] rounded-lg p-3 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#8A8F98] flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-[#5E6AD2]" /> What-If Recovery Simulator
              </span>
              <span
                className={`font-mono font-semibold px-2 py-0.5 rounded text-[11px] ${
                  isRecovered
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                    : "bg-rose-500/10 text-rose-300 border border-rose-500/25"
                }`}
              >
                {isRecovered ? "ELIGIBLE ✓" : `${classesNeeded} MORE TO QUALIFY`}
              </span>
            </div>

            {/* Slider */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-[11px] text-[#8A8F98]">
                <span>Drag to simulate upcoming classes attended:</span>
                <span className="font-mono text-white font-semibold">+{sliderValue} classes</span>
              </div>
              <input
                type="range"
                min="0"
                max="5"
                step="1"
                value={sliderValue}
                onChange={(e) => setSliderValue(parseInt(e.target.value, 10))}
                className="w-full h-1.5 bg-white/[0.1] rounded-lg appearance-none cursor-pointer accent-[#5E6AD2]"
              />
            </div>

            {/* Projected Outcome Pill */}
            <div className="flex items-center justify-between text-xs pt-1 border-t border-white/[0.06]">
              <span className="text-[#8A8F98]">Projected Attendance:</span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-[#8A8F98]">
                  ({attendedProjected}/{conductedProjected})
                </span>
                <span
                  className={`font-mono text-sm font-bold ${
                    isRecovered ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  {projectedPct.toFixed(1)}%
                </span>
              </div>
            </div>

            {isRecovered ? (
              <p className="text-[11px] text-emerald-300 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                Attending the next {sliderValue} classes restores your ESE final exam eligibility!
              </p>
            ) : (
              <p className="text-[11px] text-amber-300/90 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 shrink-0" />
                Attend the next 3 consecutive lectures to cross 75.0% before next Friday.
              </p>
            )}
          </div>
        </Card>

        {/* Today's Timetable */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-[#5E6AD2]" /> Today's Routine
            </h2>
            <span className="text-[11px] font-mono text-[#8A8F98]">Thursday, 3 Classes</span>
          </div>

          <div className="space-y-1.5">
            {TODAY_SCHEDULE.map((item) => (
              <Card
                key={item.id}
                className="p-3 flex items-center justify-between hover:border-white/[0.15] cursor-pointer"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="text-center shrink-0 pr-3 border-r border-white/[0.08]">
                    <div className="text-xs font-semibold text-white font-mono">{item.time.split(" - ")[0]}</div>
                    <div className="text-[10px] text-[#8A8F98]">{item.time.split(" - ")[1]}</div>
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-xs text-white truncate">{item.subject}</span>
                      <span className="text-[10px] font-mono text-[#8A8F98] px-1 py-0.2 rounded bg-white/[0.04]">
                        {item.code}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#8A8F98] truncate">
                      {item.room} · {item.faculty}
                    </p>
                  </div>
                </div>

                <div className="shrink-0 pl-2">
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white/[0.04] text-[#9DA3AE] border border-white/[0.06]">
                    {item.type}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Quick Subject Health & Safe Bunks */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">
              All Subjects · Safe to Bunk
            </h2>
            <Link href="/attendance" className="text-[11px] text-[#5E6AD2] hover:underline flex items-center gap-1">
              Full Ledger <ChevronRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {SUBJECTS_VITALS.map((subj) => (
              <Card key={subj.code} className="p-2.5">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-mono text-[#8A8F98]">{subj.code}</span>
                  <span
                    className={`text-[10px] font-mono font-semibold ${
                      subj.status === "critical" ? "text-rose-400" : "text-emerald-400"
                    }`}
                  >
                    {subj.current}%
                  </span>
                </div>
                <div className="text-xs font-medium text-white truncate mb-1.5">{subj.name}</div>
                <div className="text-[10px] text-[#8A8F98] flex items-center justify-between">
                  <span>Safe margin:</span>
                  <span
                    className={`font-mono font-medium ${
                      subj.safeBunks === 0 ? "text-rose-300" : "text-[#ECEEF0]"
                    }`}
                  >
                    {subj.safeBunks === 0 ? "0 (At Risk)" : `${subj.safeBunks} lectures`}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* AI Study Corner CTA Card */}
        <Card className="p-3.5 border-indigo-500/30 bg-gradient-to-r from-[#12131F] to-[#0D0E10] flex items-center justify-between">
          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#5E6AD2]" />
              <span className="text-xs font-semibold text-white">AI Study Corner</span>
              <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-indigo-500/20 text-indigo-300">
                Ground in DBMS Unit 3
              </span>
            </div>
            <p className="text-[11px] text-[#9DA3AE]">
              Ask doubts on BCNF Normalization or take a 5-question mock test.
            </p>
          </div>
          <Link href="/study">
            <Button size="sm" variant="primary">
              Open Studio
            </Button>
          </Link>
        </Card>
      </div>
    </MobileLayout>
  );
}
