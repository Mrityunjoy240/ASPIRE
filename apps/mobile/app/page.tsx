"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
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
  ArrowRight,
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
  { code: "CS501", name: "DBMS", current: 73.3, threshold: 75.0, attended: 22, conducted: 30, safeBunks: 0, status: "critical" as const },
  { code: "CS502", name: "Operating Systems", current: 82.1, threshold: 75.0, attended: 23, conducted: 28, safeBunks: 2, status: "safe" as const },
  { code: "CS503", name: "Computer Networks", current: 78.6, threshold: 75.0, attended: 22, conducted: 28, safeBunks: 1, status: "safe" as const },
  { code: "CS504", name: "AI & ML", current: 88.0, threshold: 75.0, attended: 22, conducted: 25, safeBunks: 4, status: "safe" as const },
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
    <StudentLayout>
      <div className="space-y-6">
        {/* Stitch Designs Banner */}
        <div className="p-3.5 rounded-lg bg-gradient-to-r from-indigo-500/15 via-[#121316] to-[#0D0E10] border border-indigo-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Sparkles className="w-4 h-4 text-[#5E6AD2] shrink-0" />
            <div>
              <span className="text-xs font-semibold text-white">
                Stitch UI Designs Generated (3 Variants Ready)
              </span>
              <p className="text-[11px] text-[#8A8F98]">
                Compare Cozy Notion Desk, Academic Monolith, and Editorial Bento designs.
              </p>
            </div>
          </div>
          <Link href="/designs">
            <Button size="sm" variant="primary" icon={<ArrowRight className="w-3 h-3" />}>
              Compare 3 Stitch Designs
            </Button>
          </Link>
        </div>

        {/* Welcome Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-white tracking-tight">Student Command Center</h1>
              <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/25 font-medium">
                <Flame className="w-3.5 h-3.5 text-amber-400" /> 3-Day Study Streak
              </span>
            </div>
            <p className="text-xs text-[#8A8F98] mt-0.5">
              Welcome back, <span className="text-white font-medium">Ananya Roy</span> · Roll: <span className="font-mono text-white/90">BCREC/CSE/2024/042</span> · Section A
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Link href="/study">
              <Button size="md" variant="secondary" icon={<Sparkles className="w-3.5 h-3.5 text-[#5E6AD2]" />}>
                AI Study Corner
              </Button>
            </Link>
            <Link href="/plan">
              <Button size="md" variant="primary" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                Active Recovery Plan
              </Button>
            </Link>
          </div>
        </div>

        {/* Top 2-Column Grid: Hero Risk Card & What-If + Today's Priority */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left 2 Cols: Critical Attendance Alert & What-If Simulator */}
          <div className="lg:col-span-2">
            <Card className="p-5 border-rose-500/30 bg-gradient-to-b from-[#141014] to-[#0D0E10] relative overflow-hidden h-full flex flex-col justify-between">
              <div className="absolute top-0 right-0 w-64 h-64 bg-rose-500/[0.04] rounded-full blur-3xl pointer-events-none" />

              <div>
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2.5">
                    <StatusBadge variant="critical" showPulse>
                      CRITICAL RISK
                    </StatusBadge>
                    <span className="text-sm font-semibold text-white">CS501 · Database Management Systems</span>
                  </div>
                  <span className="text-xs font-mono text-rose-300 bg-rose-500/15 border border-rose-500/30 px-2.5 py-0.5 rounded font-medium">
                    ESE Exam in 8 Days
                  </span>
                </div>

                <p className="text-[13px] text-[#ECEEF0] leading-relaxed mb-4">
                  Your current attendance is <span className="text-rose-400 font-mono font-bold">73.3%</span> (22/30 lectures attended). This is below BCREC's mandatory institutional threshold of <span className="font-mono font-semibold text-white">75.0%</span>.
                </p>

                {/* What-If Simulator Box */}
                <div className="bg-[#121316] border border-white/[0.08] rounded-lg p-4 space-y-3.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-white flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-[#5E6AD2]" />
                      Interactive What-If Recovery Simulator
                    </span>
                    <span
                      className={`font-mono font-semibold px-2.5 py-0.5 rounded text-xs ${
                        isRecovered
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                          : "bg-rose-500/10 text-rose-300 border border-rose-500/25"
                      }`}
                    >
                      {isRecovered ? "ELIGIBILITY RESTORED ✓" : `${classesNeeded} MORE CONSECUTIVE CLASSES TO QUALIFY`}
                    </span>
                  </div>

                  {/* Range Slider */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs text-[#8A8F98]">
                      <span>Simulate attending upcoming classes:</span>
                      <span className="font-mono text-white font-semibold">+{sliderValue} classes</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="6"
                      step="1"
                      value={sliderValue}
                      onChange={(e) => setSliderValue(parseInt(e.target.value, 10))}
                      className="w-full h-2 bg-white/[0.1] rounded-lg appearance-none cursor-pointer accent-[#5E6AD2]"
                    />
                    <div className="flex justify-between text-[11px] font-mono text-[#6E7480]">
                      <span>0 classes (+0%)</span>
                      <span>+2 classes (75.0%)</span>
                      <span>+4 classes (76.5%)</span>
                      <span>+6 classes (77.8%)</span>
                    </div>
                  </div>

                  {/* Outcome Bar */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-white/[0.06] text-xs">
                    <span className="text-[#8A8F98]">
                      Simulated Record: <span className="font-mono text-white font-semibold">{attendedProjected}</span> of <span className="font-mono text-white font-semibold">{conductedProjected}</span> lectures
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-[#8A8F98]">Projected Attendance:</span>
                      <span
                        className={`font-mono text-base font-bold ${
                          isRecovered ? "text-emerald-400" : "text-rose-400"
                        }`}
                      >
                        {projectedPct.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Status Note */}
              <div className="mt-3 pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs">
                {isRecovered ? (
                  <p className="text-emerald-300 flex items-center gap-1.5 text-xs">
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    Attending the next {sliderValue} classes satisfies BCREC Academic Regulation Sec 4.1!
                  </p>
                ) : (
                  <p className="text-amber-300 flex items-center gap-1.5 text-xs">
                    <Clock className="w-4 h-4 shrink-0" />
                    Attend today, Friday, and Monday lectures to cross 75.0% before next week.
                  </p>
                )}
                <Link href="/plan" className="text-xs text-[#5E6AD2] hover:underline font-medium shrink-0">
                  View Mentor Plan →
                </Link>
              </div>
            </Card>
          </div>

          {/* Right 1 Col: Urgent Deadlines & Obligations */}
          <div className="space-y-4">
            <Card className="p-4 space-y-3.5 bg-[#0D0E10] border-white/[0.08] h-full flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-[#5E6AD2]" /> Due Today & Deadlines
                  </h3>
                  <span className="text-[11px] font-mono text-[#8A8F98]">2 Pending</span>
                </div>

                <div className="space-y-2.5 mt-3">
                  <div className="p-3 rounded-lg bg-[#121316] border border-white/[0.06] space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-white">DBMS CA2 Assignment</span>
                      <span className="text-[10px] font-mono text-rose-300 bg-rose-500/15 px-1.5 py-0.2 rounded">
                        Tonight 23:59
                      </span>
                    </div>
                    <p className="text-[11px] text-[#8A8F98]">
                      Functional Dependency & Canonical Cover problem set.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg bg-[#121316] border border-white/[0.06] space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-white">Unit 3 Practice Quiz</span>
                      <span className="text-[10px] font-mono text-indigo-300 bg-indigo-500/15 px-1.5 py-0.2 rounded">
                        AI Studio
                      </span>
                    </div>
                    <p className="text-[11px] text-[#8A8F98]">
                      5 questions on 3NF & BCNF to meet Day 2 recovery goal.
                    </p>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-white/[0.06]">
                <div className="flex items-center justify-between text-xs text-[#8A8F98]">
                  <span>Mentor Assigned:</span>
                  <span className="text-white font-medium">Prof. Raj Kumar Samanta</span>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Middle 2-Column Grid: Today's Routine & Safe to Bunk Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left 2 Cols: Today's Full Routine Table */}
          <div className="lg:col-span-2 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-[#5E6AD2]" /> Today's Routine & Lecture Hall Allocations
              </h2>
              <span className="text-xs font-mono text-[#8A8F98]">Thursday · 3 Sessions</span>
            </div>

            <Card className="overflow-hidden border-white/[0.08]">
              <div className="divide-y divide-white/[0.06]">
                {TODAY_SCHEDULE.map((item) => (
                  <div
                    key={item.id}
                    className="p-3.5 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
                  >
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="text-left shrink-0 pr-4 border-r border-white/[0.08]">
                        <div className="text-xs font-semibold text-white font-mono">{item.time.split(" - ")[0]}</div>
                        <div className="text-[11px] text-[#8A8F98]">{item.time.split(" - ")[1]}</div>
                      </div>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="font-semibold text-xs text-white truncate">{item.subject}</span>
                          <span className="text-[10px] font-mono text-[#8A8F98] px-1.5 py-0.2 rounded bg-white/[0.04] border border-white/[0.06]">
                            {item.code}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#8A8F98] truncate">
                          {item.room} · {item.faculty}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white/[0.04] text-[#9DA3AE] border border-white/[0.06]">
                        {item.type.toUpperCase()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Right 1 Col: Safe-to-Bunk Margin Cards */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">
                All Enrolled Courses · Margin
              </h2>
              <Link href="/attendance" className="text-xs text-[#5E6AD2] hover:underline flex items-center gap-0.5">
                Full Ledger <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-2">
              {SUBJECTS_VITALS.map((subj) => (
                <Card key={subj.code} className="p-3 hover:border-white/[0.14] transition-all">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-white">{subj.name}</span>
                      <span className="text-[10px] font-mono text-[#8A8F98]">({subj.code})</span>
                    </div>
                    <span
                      className={`text-xs font-mono font-bold ${
                        subj.status === "critical" ? "text-rose-400" : "text-emerald-400"
                      }`}
                    >
                      {subj.current}%
                    </span>
                  </div>

                  <div className="w-full h-1.5 bg-white/[0.08] rounded-full overflow-hidden mb-2">
                    <div
                      className={`h-full ${
                        subj.status === "critical" ? "bg-rose-500" : "bg-emerald-500"
                      }`}
                      style={{ width: `${subj.current}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-[#8A8F98]">
                    <span>Attended: {subj.attended}/{subj.conducted}</span>
                    <span
                      className={`font-mono font-medium ${
                        subj.safeBunks === 0 ? "text-rose-300" : "text-emerald-300"
                      }`}
                    >
                      {subj.safeBunks === 0 ? "0 safe bunks (At Risk)" : `${subj.safeBunks} safe bunks`}
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom Banner: AI Study Corner Desktop Studio */}
        <Card className="p-5 border-indigo-500/30 bg-gradient-to-r from-[#12131F] via-[#0D0E10] to-[#0A0B0E] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#5E6AD2]" />
              <h3 className="text-sm font-semibold text-white">AI Study Studio Grounded on BCREC Syllabus</h3>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                NotebookLM Model
              </span>
            </div>
            <p className="text-xs text-[#9DA3AE]">
              Ask doubts, practice 5-mark conceptual derivations, or take auto-generated practice quizzes grounded on actual college notes.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <Link href="/study">
              <Button size="md" variant="primary" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                Launch Study Studio
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    </StudentLayout>
  );
}
