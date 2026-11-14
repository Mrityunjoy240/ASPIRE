"use client";

import React, { useState } from "react";
import Link from "next/link";
import { MobileLayout } from "@/components/MobileLayout";
import { Card } from "@/components/ui/Card";
import {
  Milestone,
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

export default function StudentPlanPage() {
  const [actions, setActions] = useState<ActionItem[]>(INITIAL_ACTIONS);

  const toggleAction = (id: string) => {
    setActions((prev) =>
      prev.map((act) => (act.id === id ? { ...act, completed: !act.completed } : act))
    );
  };

  const completedCount = actions.filter((a) => a.completed).length;
  const progressPercent = Math.round((completedCount / actions.length) * 100);

  return (
    <MobileLayout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-white tracking-tight">Academic Recovery Plan</h1>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                ACTIVE
              </span>
            </div>
            <p className="text-xs text-[#8A8F98]">
              Case ID: <span className="font-mono text-white">CAS-BCREC-2026-0042</span> · CS501 DBMS
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-[#8A8F98] bg-[#121316] border border-white/[0.08] px-2.5 py-1 rounded-md">
            <UserCheck className="w-3.5 h-3.5 text-[#5E6AD2]" />
            <span>Approved by Mentor</span>
          </div>
        </div>

        {/* Plan Overview & Progress Bar */}
        <Card className="p-4 border-indigo-500/30 bg-gradient-to-r from-[#12131F] to-[#0D0E10] space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-white">14-Day Exam Eligibility Roadmap</span>
            <span className="font-mono text-xs text-indigo-300 font-bold">{progressPercent}% Completed</span>
          </div>

          {/* Progress Track */}
          <div className="w-full h-2 bg-white/[0.08] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#5E6AD2] to-emerald-400 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-[#8A8F98]">
            <span>{completedCount} of {actions.length} recovery milestones met</span>
            <span className="text-emerald-400 font-mono font-medium">Exam Date: 22 Nov 2026</span>
          </div>
        </Card>

        {/* Structured Evidence Panel */}
        <Card className="p-3.5 space-y-2 bg-[#0D0E10] border-white/[0.08]">
          <span className="text-[11px] font-semibold text-[#8A8F98] uppercase tracking-wider block">
            Why This Plan Was Created (Ground Truth Evidence):
          </span>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-2 rounded bg-[#121316] border border-white/[0.04]">
              <span className="text-[10px] text-[#8A8F98] block">Current Attendance</span>
              <span className="font-mono font-bold text-rose-400">73.3%</span>
              <span className="text-[10px] text-[#8A8F98] ml-1">(22/30 classes)</span>
            </div>
            <div className="p-2 rounded bg-[#121316] border border-white/[0.04]">
              <span className="text-[10px] text-[#8A8F98] block">Required Threshold</span>
              <span className="font-mono font-bold text-white">75.0%</span>
              <span className="text-[10px] text-[#8A8F98] ml-1">(BCREC Rule)</span>
            </div>
            <div className="p-2 rounded bg-[#121316] border border-white/[0.04]">
              <span className="text-[10px] text-[#8A8F98] block">Exam Proximity</span>
              <span className="font-mono font-bold text-amber-400">8 Days Left</span>
              <span className="text-[10px] text-[#8A8F98] ml-1">(Urgency Band: Critical)</span>
            </div>
            <div className="p-2 rounded bg-[#121316] border border-white/[0.04]">
              <span className="text-[10px] text-[#8A8F98] block">Syllabus Weak Area</span>
              <span className="font-semibold text-white">Unit 3 Normalization</span>
            </div>
          </div>
        </Card>

        {/* Action Milestones List */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
              <Milestone className="w-3.5 h-3.5 text-[#5E6AD2]" /> Your Daily Milestones
            </h2>
            <span className="text-[11px] text-[#8A8F98]">Tap checkbox to update progress</span>
          </div>

          <div className="space-y-2">
            {actions.map((act) => (
              <Card
                key={act.id}
                className={`p-3.5 transition-all ${
                  act.completed ? "border-emerald-500/25 bg-[#0A120E]" : "border-white/[0.08] hover:border-white/[0.14]"
                }`}
              >
                <div className="flex items-start gap-3">
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
                      <span className="text-[10px] font-mono text-[#8A8F98] shrink-0">{act.duration}</span>
                    </div>

                    <p className="text-[11px] text-[#8A8F98] mt-1 leading-relaxed">{act.desc}</p>

                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.04] text-[10px]">
                      <span className="text-[#8A8F98]">Due: {act.deadline}</span>

                      {act.category === "study" && (
                        <Link href="/study">
                          <span className="text-[#5E6AD2] hover:underline flex items-center gap-1">
                            Open Study Corner <ArrowRight className="w-2.5 h-2.5" />
                          </span>
                        </Link>
                      )}
                      {act.category === "quiz" && (
                        <Link href="/study">
                          <span className="text-[#5E6AD2] hover:underline flex items-center gap-1">
                            Launch Practice Quiz <ArrowRight className="w-2.5 h-2.5" />
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

        {/* Immutable Audit Trail Card */}
        <Card className="p-3 bg-[#0A0B0D] border-white/[0.06] space-y-1.5 text-[11px] text-[#8A8F98]">
          <span className="text-[10px] font-mono text-[#6E7480] uppercase tracking-wider block">
            Institutional Audit Trail
          </span>
          <div className="space-y-1 font-mono text-[10px]">
            <p>• 07 Oct 09:30: Risk detected by Rule Engine v2.1 (73.3% attendance)</p>
            <p>• 07 Oct 09:31: Adaptive Learning Agent synthesized 14-day recovery path</p>
            <p>• 07 Oct 11:15: Plan formally approved by Mentor Prof. Raj Kumar Samanta</p>
            <p>• 07 Oct 14:00: Plan acknowledged and active on Student Portal</p>
          </div>
        </Card>
      </div>
    </MobileLayout>
  );
}
