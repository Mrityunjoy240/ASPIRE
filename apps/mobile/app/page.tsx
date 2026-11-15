"use client";

import React from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { AestheticWidgets } from "@/components/widgets/AestheticWidgets";
import {
  BookOpen,
  Sparkles,
  ArrowRight,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  School,
  Upload,
  Calendar,
  Layers,
  Award,
} from "lucide-react";

interface SubjectDesk {
  id: string;
  code: string;
  title: string;
  faculty: string;
  room: string;
  color: string;
  gradient: string;
  emoji: string;
  currentUnit: string;
  notesCount: number;
  pendingAssignments: number;
  studyProgress: number;
  tag: string;
}

const ENROLLED_SUBJECTS: SubjectDesk[] = [
  {
    id: "cs501",
    code: "CS501",
    title: "Database Management Systems",
    faculty: "Prof. Raj Kumar Samanta",
    room: "Room 302",
    color: "#5E6AD2",
    gradient: "from-indigo-950/60 via-purple-950/40 to-[#161616]",
    emoji: "🗄️",
    currentUnit: "Unit 3: Normalization & Functional Dependencies",
    notesCount: 14,
    pendingAssignments: 1,
    studyProgress: 65,
    tag: "ESE in 8 Days",
  },
  {
    id: "cs502",
    code: "CS502",
    title: "Operating Systems",
    faculty: "Dr. Anirban Bose",
    room: "Room 304",
    color: "#38bdf8",
    gradient: "from-sky-950/60 via-cyan-950/40 to-[#161616]",
    emoji: "💻",
    currentUnit: "Unit 2: CPU Scheduling & Process Sync",
    notesCount: 11,
    pendingAssignments: 0,
    studyProgress: 48,
    tag: "Unit 2 Clear",
  },
  {
    id: "cs503",
    code: "CS503",
    title: "Computer Networks",
    faculty: "Prof. Sunita Roy",
    room: "Room 201",
    color: "#34d399",
    gradient: "from-emerald-950/60 via-teal-950/40 to-[#161616]",
    emoji: "🌐",
    currentUnit: "Unit 3: TCP Congestion & Sliding Window",
    notesCount: 9,
    pendingAssignments: 1,
    studyProgress: 35,
    tag: "CA3 Next Week",
  },
  {
    id: "cs504",
    code: "CS504",
    title: "Artificial Intelligence & ML",
    faculty: "Dr. Subrata Mukherjee",
    room: "Lab 3",
    color: "#f59e0b",
    gradient: "from-amber-950/60 via-orange-950/40 to-[#161616]",
    emoji: "🤖",
    currentUnit: "Unit 4: Deep Learning & Neural Networks",
    notesCount: 8,
    pendingAssignments: 0,
    studyProgress: 52,
    tag: "Lab Project Due",
  },
];

export default function StudentStudyDeskPage() {
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
                  Stitch Themes
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

              {/* Top Quick Actions */}
              <div className="flex items-center gap-2">
                <Link href="/classroom">
                  <Button size="sm" variant="secondary" icon={<School className="w-3.5 h-3.5 text-emerald-400" />}>
                    All Classrooms
                  </Button>
                </Link>
                <Link href="/study?subject=cs501">
                  <Button size="sm" variant="primary" icon={<Sparkles className="w-3.5 h-3.5" />}>
                    Open Study Studio
                  </Button>
                </Link>
              </div>
            </div>

            {/* Greeting & Subtitle */}
            <div className="space-y-1">
              <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
                My Study Desk ☕
              </h1>
              <p className="text-xs text-[#9d9b97]">
                Welcome back, Ananya · BCREC CSE 3rd Year (Sem 5) · <span className="italic text-[#ECEEF0]">"Focus on the process, results will follow."</span>
              </p>
            </div>

            {/* Metadata Chips (Notion Properties) */}
            <div className="flex flex-wrap items-center gap-2 pt-3">
              <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-[#b4a0e5]/10 text-[#b4a0e5] border border-[#b4a0e5]/25 flex items-center gap-1.5 font-medium">
                🎯 Active Target: CS501 Normalization
              </span>
              <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-[#e6ba7e]/10 text-[#e6ba7e] border border-[#e6ba7e]/25 flex items-center gap-1.5 font-medium">
                🔥 3-Day Focus Streak
              </span>
              <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-rose-500/10 text-rose-300 border border-rose-500/25 flex items-center gap-1.5 font-medium">
                ⚠️ 1 Assignment Due Tonight
              </span>
              <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-[#9ec899]/10 text-[#9ec899] border border-[#9ec899]/25 flex items-center gap-1.5 font-medium">
                📍 Room 302 @ 10:00 AM
              </span>
            </div>
          </div>
        </div>

        {/* ======================================================== */}
        {/* 2. NOTION AESTHETIC WIDGETS ROW (Pomodoro, Clock, Streak)*/}
        {/* ======================================================== */}
        <AestheticWidgets />

        {/* ======================================================== */}
        {/* 3. YOUR SUBJECT NOTEBOOKS & CLASSROOMS                   */}
        {/* ======================================================== */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-lg">📚</span>
              <div>
                <h2 className="text-base font-bold text-white tracking-tight">Your Subject Desks</h2>
                <p className="text-xs text-[#8A8F98]">Pick a subject to launch its AI NotebookLM studio or open its classroom</p>
              </div>
            </div>
            <Link href="/classroom" className="text-xs text-[#5E6AD2] hover:text-indigo-400 font-medium flex items-center gap-1">
              View All Classrooms <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {ENROLLED_SUBJECTS.map((sub) => (
              <Card
                key={sub.id}
                className="bg-[#18181A] border-white/[0.08] hover:border-white/[0.18] transition-all overflow-hidden flex flex-col justify-between group shadow-md"
              >
                <div>
                  {/* Subject Cover Banner */}
                  <div className={`h-20 w-full bg-gradient-to-r ${sub.gradient} p-3.5 flex items-start justify-between border-b border-white/[0.06] relative`}>
                    <div className="flex items-center gap-2.5">
                      <span className="text-2xl p-1.5 rounded-xl bg-black/40 backdrop-blur-md border border-white/[0.1] select-none">
                        {sub.emoji}
                      </span>
                      <div>
                        <span className="text-[11px] font-mono font-bold text-white/90 block">
                          {sub.code}
                        </span>
                        <span className="text-[11px] text-white/70">
                          {sub.room} · {sub.faculty}
                        </span>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-black/50 backdrop-blur-md text-[#e6ba7e] border border-white/[0.1] font-semibold">
                      {sub.tag}
                    </span>
                  </div>

                  {/* Body Content */}
                  <div className="p-4 space-y-3">
                    <div>
                      <h3 className="text-base font-bold text-white group-hover:text-indigo-400 transition-colors">
                        {sub.title}
                      </h3>
                      <p className="text-xs text-[#8A8F98] mt-0.5 flex items-center gap-1.5">
                        <BookOpen className="w-3 h-3 text-[#5E6AD2]" />
                        {sub.currentUnit}
                      </p>
                    </div>

                    {/* Meta stats pills */}
                    <div className="flex items-center gap-2 text-xs">
                      <span className="px-2 py-1 rounded bg-[#121214] border border-white/[0.06] text-[#ECEEF0] flex items-center gap-1 text-[11px]">
                        <FileText className="w-3 h-3 text-indigo-400" />
                        {sub.notesCount} Lecture Notes
                      </span>
                      {sub.pendingAssignments > 0 ? (
                        <span className="px-2 py-1 rounded bg-rose-500/10 border border-rose-500/20 text-rose-300 font-medium flex items-center gap-1 text-[11px]">
                          <AlertCircle className="w-3 h-3 text-rose-400" />
                          {sub.pendingAssignments} Assignment Due
                        </span>
                      ) : (
                        <span className="px-2 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 flex items-center gap-1 text-[11px]">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          All Done ✓
                        </span>
                      )}
                    </div>

                    {/* Progress Bar */}
                    <div className="space-y-1 pt-0.5">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-[#8A8F98]">Syllabus Revision</span>
                        <span className="font-mono text-white font-medium">{sub.studyProgress}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-indigo-500 to-[#e6ba7e] rounded-full"
                          style={{ width: `${sub.studyProgress}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bottom 2-Button Action Bar: Study Studio vs Classroom */}
                <div className="p-4 pt-0 grid grid-cols-2 gap-2 border-t border-white/[0.04] mt-2">
                  <Link href={`/study?subject=${sub.id}`}>
                    <Button
                      size="sm"
                      variant="primary"
                      className="w-full text-xs font-semibold"
                      icon={<Sparkles className="w-3.5 h-3.5 text-amber-300" />}
                    >
                      ⚡ Study Studio
                    </Button>
                  </Link>

                  <Link href={`/classroom/${sub.id}`}>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="w-full text-xs font-semibold"
                      icon={<School className="w-3.5 h-3.5 text-[#8A8F98]" />}
                    >
                      📁 Classroom
                    </Button>
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* ======================================================== */}
        {/* 4. QUICK STUDY RESUME & PENDING HOMEWORK SHELF           */}
        {/* ======================================================== */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Pick Up Where You Left Off */}
          <div className="p-4 rounded-xl bg-gradient-to-br from-[#1C1A24] via-[#16171E] to-[#141518] border border-indigo-500/25 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold uppercase">
                Resume Studying
              </span>
              <span className="text-xs text-[#8A8F98]">3 hours ago</span>
            </div>

            <div>
              <h3 className="text-sm font-bold text-white">
                CS501 DBMS · Unit 3: Normalization
              </h3>
              <p className="text-xs text-[#9d9b97] mt-0.5">
                Slide 42 of 64 · Prof. Samanta · 3NF vs BCNF dependency preservation rule
              </p>
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-xs font-mono text-[#8A8F98]">Progress: 65%</span>
              <Link href="/study?subject=cs501">
                <Button size="sm" variant="primary" icon={<ArrowRight className="w-3 h-3" />}>
                  Jump to Studio
                </Button>
              </Link>
            </div>
          </div>

          {/* Tonight's Urgent Assignment Box */}
          <div className="p-4 rounded-xl bg-[#1A1816] border border-amber-500/25 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-semibold uppercase flex items-center gap-1">
                <Clock className="w-3 h-3" /> Due Tonight 11:59 PM
              </span>
              <span className="text-xs text-amber-300 font-mono">10 Marks</span>
            </div>

            <div>
              <h3 className="text-sm font-bold text-white">
                CS501 CA2: Functional Dependency Canonical Covers
              </h3>
              <p className="text-xs text-[#9d9b97] mt-0.5">
                3 Questions on Armstrong's axioms & minimal cover computation. Upload PDF.
              </p>
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-rose-300 font-mono">⚠️ Pending Submission</span>
              <Link href="/classroom/cs501">
                <Button size="sm" variant="secondary" icon={<Upload className="w-3 h-3 text-amber-300" />}>
                  Submit in Classroom
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </StudentLayout>
  );
}
