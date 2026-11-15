"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { AestheticWidgets } from "@/components/widgets/AestheticWidgets";
import {
  BookOpen,
  Calendar,
  Sparkles,
  ArrowRight,
  Clock,
  CheckCircle2,
  AlertCircle,
  Briefcase,
  Flame,
  FileText,
  SlidersHorizontal,
  ChevronRight,
  Lightbulb,
  ExternalLink,
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
    time: "10:00 - 11:15 AM",
    subject: "Database Management Systems",
    code: "CS501",
    room: "Room 302",
    faculty: "Prof. Raj Kumar Samanta",
    type: "lecture",
    status: "upcoming",
  },
  {
    id: "s2",
    time: "11:30 - 12:45 PM",
    subject: "Operating Systems",
    code: "CS502",
    room: "Room 304",
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

export default function StudentStudyDeskPage() {
  const [sliderValue, setSliderValue] = useState(0);

  // Attendance simulation math
  const attendedInitial = 22;
  const conductedInitial = 30;
  const threshold = 75.0;
  const attendedProjected = attendedInitial + sliderValue;
  const conductedProjected = conductedInitial + sliderValue;
  const projectedPct = (attendedProjected / conductedProjected) * 100;
  const isRecovered = projectedPct >= threshold;
  const classesNeeded = isRecovered ? 0 : Math.max(0, 3 - sliderValue);

  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* ======================================================== */}
        {/* 1. NOTION AESTHETIC COVER BANNER & STUDENT HEADER        */}
        {/* ======================================================== */}
        <div className="rounded-2xl border border-white/[0.08] bg-[#161616] overflow-hidden relative shadow-lg">
          {/* Aesthetic Cover Art Strip */}
          <div className="h-28 w-full bg-gradient-to-r from-[#201c24] via-[#1b1e28] to-[#17201c] relative">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-500/10 via-transparent to-transparent pointer-events-none" />
            
            {/* Quick Stitch Design Switcher Badge */}
            <div className="absolute top-3 right-3">
              <Link href="/designs">
                <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-black/60 backdrop-blur-md text-white/90 border border-white/[0.12] hover:border-white/[0.25] transition-all flex items-center gap-1.5 cursor-pointer">
                  <Sparkles className="w-3 h-3 text-[#e6ba7e]" />
                  Stitch Notion Themes (3 Designs)
                </span>
              </Link>
            </div>
          </div>

          {/* Floating Emoji Icon + Greeting */}
          <div className="px-6 pb-6 pt-0 relative">
            <div className="-mt-8 mb-3 flex items-end justify-between">
              {/* Floating Notion Avatar */}
              <div className="w-16 h-16 rounded-2xl bg-[#1E1E1E] border-2 border-[#161616] shadow-xl flex items-center justify-center text-2xl select-none">
                ✨
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-2">
                <Link href="/study">
                  <Button size="sm" variant="secondary" icon={<BookOpen className="w-3.5 h-3.5 text-[#5E6AD2]" />}>
                    Study Vault
                  </Button>
                </Link>
                <Link href="/plan">
                  <Button size="sm" variant="primary" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                    Recovery Plan
                  </Button>
                </Link>
              </div>
            </div>

            {/* Greeting & Subtitle */}
            <div className="space-y-1">
              <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
                Good morning, Ananya ☀️
              </h1>
              <p className="text-xs text-[#9d9b97]">
                Thursday, 14 November 2026 · BCREC CSE 3rd Year (Sem 5) · <span className="italic text-[#ECEEF0]">"Consistency beats intensity"</span>
              </p>
            </div>

            {/* Metadata Chips (Notion Properties) */}
            <div className="flex flex-wrap items-center gap-2 pt-3">
              <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-[#b4a0e5]/10 text-[#b4a0e5] border border-[#b4a0e5]/25 flex items-center gap-1.5 font-medium">
                🎯 Focus: DBMS Unit 3
              </span>
              <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-[#e6ba7e]/10 text-[#e6ba7e] border border-[#e6ba7e]/25 flex items-center gap-1.5 font-medium">
                🔥 3-Day Study Streak
              </span>
              <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-[#9ec899]/10 text-[#9ec899] border border-[#9ec899]/25 flex items-center gap-1.5 font-medium">
                📍 Room 302 @ 10:00 AM
              </span>
              <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-rose-500/10 text-rose-300 border border-rose-500/25 flex items-center gap-1.5 font-medium">
                ⚠️ CS501 Exam in 8 Days
              </span>
            </div>
          </div>
        </div>

        {/* ======================================================== */}
        {/* 2. NOTION AESTHETIC WIDGETS ROW (Pomodoro, Clock, Streak)*/}
        {/* ======================================================== */}
        <AestheticWidgets />

        {/* ======================================================== */}
        {/* 3. HERO "RESUME STUDYING" SHELF                          */}
        {/* ======================================================== */}
        <div className="p-4 rounded-xl bg-gradient-to-r from-[#1E1C24] via-[#18191E] to-[#141518] border border-indigo-500/25 relative overflow-hidden flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5 max-w-2xl">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold uppercase">
                Resume Studying
              </span>
              <span className="text-xs text-[#8A8F98]">Last reviewed 3 hours ago</span>
            </div>

            <h2 className="text-sm font-bold text-white">
              CS501 Database Management Systems · Unit 3: Normalization & Functional Dependencies
            </h2>

            <p className="text-xs text-[#9d9b97] leading-relaxed">
              Slide 42 of 64 by Prof. Samanta · <span className="text-[#ECEEF0]">3NF vs BCNF dependency preservation rule quick recap</span>
            </p>

            {/* Reading progress bar */}
            <div className="flex items-center gap-3 pt-1">
              <div className="w-48 h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
                <div className="h-full bg-indigo-400 rounded-full" style={{ width: "65%" }} />
              </div>
              <span className="text-[11px] font-mono text-[#8A8F98]">65% Completed</span>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <Link href="/study">
              <Button size="md" variant="primary" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                Resume Reading
              </Button>
            </Link>
            <Link href="/study/quizzes">
              <Button size="md" variant="secondary" icon={<Sparkles className="w-3.5 h-3.5 text-[#5E6AD2]" />}>
                5-Min Quiz
              </Button>
            </Link>
          </div>
        </div>

        {/* ======================================================== */}
        {/* 4. THREE NOTION GALLERY CARDS (Study, Routine, Career)   */}
        {/* ======================================================== */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">
              Academic Life & Workspaces
            </span>
            <span className="text-xs font-mono text-[#8A8F98]">BCREC CSE · 3rd Year</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* CARD 1: 🧠 STUDY CORNER (THE VAULT) */}
            <Card className="bg-[#191919] border-white/[0.08] hover:border-white/[0.18] transition-all overflow-hidden flex flex-col justify-between group">
              <div>
                {/* Mini cover strip */}
                <div className="h-20 w-full bg-gradient-to-r from-indigo-900/30 to-purple-900/20 p-3 flex items-start justify-between border-b border-white/[0.06]">
                  <span className="text-lg">🧠</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30 font-semibold">
                    ESE in 8 Days
                  </span>
                </div>

                <div className="p-4 space-y-2.5">
                  <div>
                    <h3 className="text-sm font-bold text-white group-hover:text-[#5E6AD2] transition-colors">
                      Study Corner Vault
                    </h3>
                    <p className="text-xs text-[#8A8F98] mt-0.5">
                      4 Enrolled Subjects · 42 Lecture Notes · 8 Exam Cheat Sheets
                    </p>
                  </div>

                  <div className="space-y-1.5 pt-1 text-xs">
                    <div className="flex items-center justify-between p-1.5 rounded bg-[#121212] border border-white/[0.04]">
                      <span className="text-[#ECEEF0]">CS501 DBMS</span>
                      <span className="text-[10px] font-mono text-amber-300">Unit 3 Target</span>
                    </div>
                    <div className="flex items-center justify-between p-1.5 rounded bg-[#121212] border border-white/[0.04]">
                      <span className="text-[#ECEEF0]">CS502 Operating Systems</span>
                      <span className="text-[10px] font-mono text-emerald-400">Unit 2 Clear ✓</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-4 pt-0">
                <Link href="/study" className="block">
                  <Button size="sm" variant="secondary" className="w-full" icon={<ArrowRight className="w-3 h-3" />}>
                    Open Study Vault
                  </Button>
                </Link>
              </div>
            </Card>

            {/* CARD 2: 📅 TODAY'S ROUTINE & MARGINS */}
            <Card className="bg-[#191919] border-white/[0.08] hover:border-white/[0.18] transition-all overflow-hidden flex flex-col justify-between group">
              <div>
                {/* Mini cover strip */}
                <div className="h-20 w-full bg-gradient-to-r from-sky-900/30 to-blue-900/20 p-3 flex items-start justify-between border-b border-white/[0.06]">
                  <span className="text-lg">📅</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold">
                    3 Sessions Today
                  </span>
                </div>

                <div className="p-4 space-y-2.5">
                  <div>
                    <h3 className="text-sm font-bold text-white group-hover:text-sky-400 transition-colors">
                      Today's Routine & Margins
                    </h3>
                    <p className="text-xs text-[#8A8F98] mt-0.5">
                      Thursday Schedule · Lecture Halls & Labs
                    </p>
                  </div>

                  <div className="space-y-1.5 pt-1 text-xs">
                    {TODAY_SCHEDULE.slice(0, 2).map((item) => (
                      <div key={item.id} className="p-1.5 rounded bg-[#121212] border border-white/[0.04] flex items-center justify-between">
                        <div>
                          <span className="font-semibold text-white">{item.code}</span>
                          <span className="text-[11px] text-[#8A8F98] ml-1.5">{item.room}</span>
                        </div>
                        <span className="text-[10px] font-mono text-[#8A8F98]">{item.time.split(" - ")[0]}</span>
                      </div>
                    ))}
                  </div>

                  {/* Safe bunk alert */}
                  <div className="p-2 rounded bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-300">
                    ⚠️ 0 safe bunks in DBMS (73.3%) — attend today!
                  </div>
                </div>
              </div>

              <div className="p-4 pt-0">
                <Link href="/attendance" className="block">
                  <Button size="sm" variant="secondary" className="w-full" icon={<ArrowRight className="w-3 h-3" />}>
                    View Full Ledger
                  </Button>
                </Link>
              </div>
            </Card>

            {/* CARD 3: 🚀 CAREER & PLACEMENT READINESS */}
            <Card className="bg-[#191919] border-white/[0.08] hover:border-white/[0.18] transition-all overflow-hidden flex flex-col justify-between group">
              <div>
                {/* Mini cover strip */}
                <div className="h-20 w-full bg-gradient-to-r from-emerald-900/30 to-teal-900/20 p-3 flex items-start justify-between border-b border-white/[0.06]">
                  <span className="text-lg">🚀</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold">
                    88% SDE Match
                  </span>
                </div>

                <div className="p-4 space-y-2.5">
                  <div>
                    <h3 className="text-sm font-bold text-white group-hover:text-emerald-400 transition-colors">
                      Career & Placement Hub
                    </h3>
                    <p className="text-xs text-[#8A8F98] mt-0.5">
                      B.Tech CSE Autonomous · Honors Track
                    </p>
                  </div>

                  <div className="space-y-1.5 pt-1 text-xs">
                    <div className="flex items-center justify-between p-1.5 rounded bg-[#121212] border border-white/[0.04]">
                      <span className="text-[#ECEEF0]">Cumulative CGPA</span>
                      <span className="font-mono font-bold text-emerald-400">8.21 / 10 (Rank 14)</span>
                    </div>
                    <div className="flex items-center justify-between p-1.5 rounded bg-[#121212] border border-white/[0.04]">
                      <span className="text-[#ECEEF0]">Active Backlogs</span>
                      <span className="font-mono font-bold text-emerald-400">0 Backlogs ✓</span>
                    </div>
                    <div className="flex items-center justify-between p-1.5 rounded bg-[#121212] border border-white/[0.04]">
                      <span className="text-[#ECEEF0]">Recruiters Eligible</span>
                      <span className="font-mono text-emerald-300">TCS, Wipro, Capgemini</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-4 pt-0">
                <Link href="/career/placements" className="block">
                  <Button size="sm" variant="secondary" className="w-full" icon={<ArrowRight className="w-3 h-3" />}>
                    Open Placement Hub
                  </Button>
                </Link>
              </div>
            </Card>
          </div>
        </div>

        {/* ======================================================== */}
        {/* 5. NOTION-STYLE CALLOUT BOXES                            */}
        {/* ======================================================== */}
        <div className="p-4 rounded-xl bg-[#1A1816] border border-amber-500/25 flex items-start gap-3">
          <span className="text-xl shrink-0 mt-0.5">💡</span>
          <div className="space-y-1 text-xs">
            <span className="font-bold text-amber-200">
              Exam Submission Deadline Reminder:
            </span>
            <p className="text-[#ECEEF0] leading-relaxed">
              Tonight at 11:59 PM is the submission deadline for <span className="text-white font-semibold">CS501 DBMS CA2 Assignment</span> (Functional Dependency Canonical Covers). Complete the 3 questions and upload your solution PDF.
            </p>
          </div>
        </div>

        {/* ======================================================== */}
        {/* 6. WHAT-IF ATTENDANCE RESTORATION SIMULATOR              */}
        {/* ======================================================== */}
        <Card className="p-5 bg-[#191919] border-white/[0.08] space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-[#5E6AD2]" />
              <h3 className="text-sm font-bold text-white">
                Interactive What-If Recovery Simulator (CS501 DBMS)
              </h3>
            </div>
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

          <p className="text-xs text-[#9d9b97]">
            Your current attendance is <span className="font-mono text-rose-400 font-semibold">73.3%</span> (22/30 lectures). Drag the slider to project attending upcoming lectures:
          </p>

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
              <span>0 classes (73.3%)</span>
              <span>+2 classes (75.0% ✓)</span>
              <span>+4 classes (76.5%)</span>
              <span>+6 classes (77.8%)</span>
            </div>
          </div>

          <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-xs text-[#8A8F98]">
            <span>
              Simulated: <span className="font-mono text-white font-semibold">{attendedProjected}</span> of <span className="font-mono text-white font-semibold">{conductedProjected}</span> lectures
            </span>
            <div className="flex items-center gap-2">
              <span>Projected Attendance:</span>
              <span className={`font-mono text-base font-bold ${isRecovered ? "text-emerald-400" : "text-rose-400"}`}>
                {projectedPct.toFixed(1)}%
              </span>
            </div>
          </div>
        </Card>
      </div>
    </StudentLayout>
  );
}
