"use client";

import React from "react";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Award,
  TrendingUp,
  CheckCircle2,
  Download,
} from "lucide-react";

const SEMESTERS = [
  { sem: "Semester 1", sgpa: 8.40, credits: 21, status: "Passed (Clear)" },
  { sem: "Semester 2", sgpa: 8.25, credits: 21, status: "Passed (Clear)" },
  { sem: "Semester 3", sgpa: 7.90, credits: 22, status: "Passed (Clear)" },
  { sem: "Semester 4", sgpa: 8.30, credits: 23, status: "Passed (Clear)" },
  { sem: "Semester 5", sgpa: 8.10, credits: 21, status: "In Progress (Current)" },
];

export default function CareerAndGradesPage() {
  const cgpa = 8.21;
  const earnedCredits = 108;
  const totalCredits = 160;
  const creditPercent = Math.round((earnedCredits / totalCredits) * 100);

  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Academic Career & Degree Audit</h1>
            <p className="text-xs text-[#8A8F98] mt-0.5">
              Degree: <span className="text-white font-medium">B.Tech in Computer Science & Engineering</span> · BCREC Autonomous
            </p>
          </div>
          <Button size="md" variant="secondary" icon={<Download className="w-3.5 h-3.5 text-[#5E6AD2]" />}>
            Download Official Grade Sheet
          </Button>
        </div>

        {/* 3-Card Summary Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4 space-y-1 bg-[#0D0E10] border-white/[0.08]">
            <div className="flex items-center justify-between text-xs text-[#8A8F98]">
              <span>Cumulative CGPA</span>
              <span className="text-emerald-400 font-mono font-semibold">+0.12 vs Sem 3</span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">{cgpa}</div>
            <p className="text-[11px] text-[#8A8F98]">
              Department Rank: <span className="font-mono text-white font-semibold">14 / 180</span> students
            </p>
          </Card>

          <Card className="p-4 space-y-1 bg-[#0D0E10] border-white/[0.08]">
            <div className="flex items-center justify-between text-xs text-[#8A8F98]">
              <span>Degree Credits Earned</span>
              <span className="text-indigo-300 font-mono font-semibold">{creditPercent}%</span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {earnedCredits} <span className="text-xs text-[#8A8F98] font-normal">/ {totalCredits}</span>
            </div>
            <p className="text-[11px] text-[#8A8F98]">52 Credits remaining for B.Tech graduation</p>
          </Card>

          <Card className="p-4 space-y-1 bg-[#0D0E10] border-white/[0.08]">
            <div className="flex items-center justify-between text-xs text-[#8A8F98]">
              <span>Active Backlogs</span>
              <span className="text-emerald-400 font-mono font-semibold">Clean Record</span>
            </div>
            <div className="text-2xl font-bold font-mono text-emerald-400">0</div>
            <p className="text-[11px] text-emerald-300 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Eligible for Autonomous Honors Degree
            </p>
          </Card>
        </div>

        {/* 2-Column Desktop Grid: Left SGPA Trajectory Table (8 Cols), Right Honors Eligibility & Audit (4 Cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Semester-wise Breakdown (8 Cols) */}
          <div className="lg:col-span-8 space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-[#5E6AD2]" /> Semester-by-Semester Progression
            </span>

            <Card className="overflow-hidden border-white/[0.08]">
              <div className="divide-y divide-white/[0.06]">
                {SEMESTERS.map((sem, idx) => (
                  <div key={idx} className="p-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors">
                    <div>
                      <div className="text-sm font-semibold text-white">{sem.sem}</div>
                      <div className="text-xs text-[#8A8F98]">{sem.credits} Credits Allocated</div>
                    </div>

                    <div className="flex items-center gap-4">
                      <span
                        className={`text-xs font-mono px-2 py-0.5 rounded ${
                          sem.status.includes("Current")
                            ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/25"
                            : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25"
                        }`}
                      >
                        {sem.status}
                      </span>
                      <div className="text-right">
                        <span className="text-base font-bold font-mono text-white">{sem.sgpa.toFixed(2)}</span>
                        <span className="block text-[10px] text-[#8A8F98]">SGPA</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Right Column: Honors Degree & Graduation Audit (4 Cols) */}
          <div className="lg:col-span-4 space-y-4">
            <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">
                <Award className="w-4 h-4 text-amber-400" /> Honors Eligibility Criteria
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="flex items-center justify-between p-2 rounded bg-[#121316]">
                  <span className="text-[#ECEEF0]">Minimum CGPA: ≥ 8.00</span>
                  <span className="text-emerald-400 font-mono font-semibold">8.21 ✓</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-[#121316]">
                  <span className="text-[#ECEEF0]">No Backlogs (History)</span>
                  <span className="text-emerald-400 font-mono font-semibold">0 Backlogs ✓</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-[#121316]">
                  <span className="text-[#ECEEF0]">MOOCs / NPTEL Credits</span>
                  <span className="text-amber-300 font-mono font-semibold">4 / 8 Credits</span>
                </div>
              </div>

              <div className="pt-2 border-t border-white/[0.06]">
                <p className="text-[11px] text-[#8A8F98] leading-relaxed">
                  Maintain attendance in DBMS above 75% to ensure ESE eligibility and keep your Honors track intact.
                </p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </StudentLayout>
  );
}
