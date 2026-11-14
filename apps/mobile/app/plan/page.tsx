"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import {
  CheckCircle2,
  ArrowRight,
  UserCheck,
} from "lucide-react";

interface ActionItem {
  id: string;
  title: string;
  category: "attendance" | "study" | "quiz" | "mentor";
  deadline: string;
  duration: string;
  completed: boolean;
  desc: string;
}

const INITIAL_ACTIONS: ActionItem[] = [
  {
    id: "act-1",
    title: "Attend Next 3 Consecutive DBMS Lectures",
    category: "attendance",
    deadline: "Before Nov 21",
    duration: "3 sessions (1/3 done)",
    completed: false,
    desc: "Attend lecture today (10 AM), Friday (10 AM), and Monday (10 AM) to cross 75.8% attendance.",
  },
  {
    id: "act-2",
    title: "Syllabus Study: 3NF & BCNF Normalization",
    category: "study",
    deadline: "Tonight 22:00",
    duration: "45 minutes",
    completed: true,
    desc: "Review functional dependencies and canonical covers in the AI Study Corner.",
  },
  {
    id: "act-3",
    title: "Pass Unit 3 Practice Checkpoint Quiz (≥70%)",
    category: "quiz",
    deadline: "Tomorrow 18:00",
    duration: "10 minutes",
    completed: false,
    desc: "Take the 5-question checkpoint quiz to prove mastery of relational decomposition.",
  },
  {
    id: "act-4",
    title: "1-on-1 Mentor Follow-Up with Prof. Samanta",
    category: "mentor",
    deadline: "Monday 15:30",
    duration: "15 minutes",
    completed: false,
    desc: "Brief meeting in Faculty Room 201 to sign off on exam condonation clearance.",
  },
];

export default function DesktopStudentPlanPage() {
  const [actions, setActions] = useState<ActionItem[]>(INITIAL_ACTIONS);

  const toggleAction = (id: string) => {
    setActions((prev) =>
      prev.map((act) => (act.id === id ? { ...act, completed: !act.completed } : act))
    );
  };

  const completedCount = actions.filter((a) => a.completed).length;
  const progressPercent = Math.round((completedCount / actions.length) * 100);

  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-white tracking-tight">Academic Recovery Plan</h1>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-semibold">
                ACTIVE
              </span>
            </div>
            <p className="text-xs text-[#8A8F98] mt-0.5">
              Case ID: <span className="font-mono text-white">CAS-BCREC-2026-0042</span> · Course: <span className="text-white font-medium">CS501 DBMS</span>
            </p>
          </div>

          <div className="flex items-center gap-2 bg-[#121316] border border-white/[0.08] px-3 py-1.5 rounded-lg text-xs text-[#9DA3AE]">
            <UserCheck className="w-4 h-4 text-[#5E6AD2]" />
            <span>Approved by Mentor: <span className="text-white font-medium">Prof. Raj Kumar Samanta</span></span>
          </div>
        </div>

        {/* 2-Column Desktop Grid: Left Milestones (7 Cols), Right Evidence & Audit (5 Cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Milestones (7 Cols) */}
          <div className="lg:col-span-7 space-y-4">
            {/* Progress Card */}
            <Card className="p-5 border-indigo-500/30 bg-gradient-to-r from-[#12131F] to-[#0D0E10] space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-white">14-Day Exam Eligibility Roadmap</span>
                <span className="font-mono text-sm text-indigo-300 font-bold">{progressPercent}% Completed</span>
              </div>

              {/* Progress Track */}
              <div className="w-full h-2 bg-white/[0.08] rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#5E6AD2] to-emerald-400 transition-all duration-300"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-xs text-[#8A8F98]">
                <span>{completedCount} of {actions.length} recovery milestones completed</span>
                <span className="text-emerald-400 font-mono font-medium">Final Exam Date: 22 Nov 2026</span>
              </div>
            </Card>

            {/* Milestones List */}
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-[#8A8F98] font-semibold uppercase tracking-wider">
                <span>Daily Recovery Actions</span>
                <span>Click checkbox to update</span>
              </div>

              <div className="space-y-2.5">
                {actions.map((act) => (
                  <Card
                    key={act.id}
                    className={`p-4 transition-all ${
                      act.completed
                        ? "border-emerald-500/25 bg-[#0A120E]"
                        : "border-white/[0.08] hover:border-white/[0.14] bg-[#0D0E10]"
                    }`}
                  >
                    <div className="flex items-start gap-3.5">
                      <button
                        onClick={() => toggleAction(act.id)}
                        className={`mt-0.5 w-5 h-5 rounded border flex items-center justify-center shrink-0 transition-colors ${
                          act.completed
                            ? "bg-emerald-500 border-emerald-500 text-white"
                            : "border-white/[0.2] hover:border-[#5E6AD2] bg-white/[0.02]"
                        }`}
                      >
                        {act.completed && <CheckCircle2 className="w-3.5 h-3.5" />}
                      </button>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className={`text-xs font-semibold ${
                              act.completed ? "text-emerald-300 line-through opacity-80" : "text-white"
                            }`}
                          >
                            {act.title}
                          </span>
                          <span className="text-[11px] font-mono text-[#8A8F98] shrink-0">{act.duration}</span>
                        </div>

                        <p className="text-xs text-[#8A8F98] mt-1 leading-relaxed">{act.desc}</p>

                        <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-white/[0.04] text-xs">
                          <span className="text-[#8A8F98]">Due: {act.deadline}</span>

                          {act.category === "study" && (
                            <Link href="/study">
                              <span className="text-[#5E6AD2] hover:underline flex items-center gap-1 font-medium">
                                Open Study Corner <ArrowRight className="w-3 h-3" />
                              </span>
                            </Link>
                          )}
                          {act.category === "quiz" && (
                            <Link href="/study">
                              <span className="text-[#5E6AD2] hover:underline flex items-center gap-1 font-medium">
                                Launch Practice Quiz <ArrowRight className="w-3 h-3" />
                              </span>
                            </Link>
                          )}
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Evidence & Audit Log (5 Cols) */}
          <div className="lg:col-span-5 space-y-4">
            {/* Ground Truth Evidence */}
            <Card className="p-4 space-y-3 bg-[#0D0E10] border-white/[0.08]">
              <span className="text-xs font-semibold text-[#8A8F98] uppercase tracking-wider block">
                Ground Truth Evidence Ledger:
              </span>

              <div className="space-y-2 text-xs">
                <div className="p-2.5 rounded bg-[#121316] border border-white/[0.04] flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-[#8A8F98] block">Current Attendance</span>
                    <span className="font-semibold text-white">22 / 30 Classes Attended</span>
                  </div>
                  <span className="font-mono font-bold text-rose-400">73.3%</span>
                </div>

                <div className="p-2.5 rounded bg-[#121316] border border-white/[0.04] flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-[#8A8F98] block">Institutional Rule</span>
                    <span className="font-semibold text-white">BCREC Academic Reg 4.1</span>
                  </div>
                  <span className="font-mono font-bold text-white">75.0% Mandatory</span>
                </div>

                <div className="p-2.5 rounded bg-[#121316] border border-white/[0.04] flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-[#8A8F98] block">Exam Proximity</span>
                    <span className="font-semibold text-white">Semester-End Exam</span>
                  </div>
                  <span className="font-mono font-bold text-amber-400">8 Days Left</span>
                </div>

                <div className="p-2.5 rounded bg-[#121316] border border-white/[0.04] flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-[#8A8F98] block">Target Syllabus Unit</span>
                    <span className="font-semibold text-white">Unit 3 Normalization</span>
                  </div>
                  <span className="font-mono font-bold text-indigo-300">Target Focus</span>
                </div>
              </div>
            </Card>

            {/* Audit Trail */}
            <Card className="p-4 bg-[#0A0B0D] border-white/[0.06] space-y-2 text-xs text-[#8A8F98]">
              <span className="text-[10px] font-mono text-[#6E7480] uppercase tracking-wider block">
                Institutional Immutable Audit Trail
              </span>
              <div className="space-y-1.5 font-mono text-[11px] leading-relaxed">
                <p>• 07 Oct 09:30: Risk detected by Rule Engine v2.1 (73.3% attendance)</p>
                <p>• 07 Oct 09:31: Adaptive Learning Agent synthesized 14-day recovery path</p>
                <p>• 07 Oct 11:15: Plan formally approved by Mentor Prof. Raj Kumar Samanta</p>
                <p>• 07 Oct 14:00: Plan active and monitored by Verification Engine</p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </StudentLayout>
  );
}
