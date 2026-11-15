"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Award,
  TrendingUp,
  CheckCircle2,
  Download,
  Briefcase,
  ChevronRight,
  AlertCircle,
  Star,
  BookOpen,
  Code2,
  Users,
  ArrowUpRight,
} from "lucide-react";

const SEMESTERS = [
  { sem: "Sem 1", sgpa: 8.40, credits: 21, status: "clear", year: "1st Year" },
  { sem: "Sem 2", sgpa: 8.25, credits: 21, status: "clear", year: "1st Year" },
  { sem: "Sem 3", sgpa: 7.90, credits: 22, status: "clear", year: "2nd Year" },
  { sem: "Sem 4", sgpa: 8.30, credits: 23, status: "clear", year: "2nd Year" },
  { sem: "Sem 5", sgpa: 8.10, credits: 21, status: "current", year: "3rd Year" },
];

const PLACEMENT_ELIGIBILITY = [
  { label: "Cumulative CGPA", value: "8.21", required: "≥ 7.0", met: true, note: "Above TCS, Wipro, and Capgemini cutoff" },
  { label: "Active Backlogs", value: "0", required: "0 Backlogs", met: true, note: "Clean academic record" },
  { label: "Overall Attendance", value: "80.2%", required: "≥ 75%", met: true, note: "Aggregate across all subjects" },
  { label: "DBMS Attendance", value: "73.3%", required: "≥ 75%", met: false, note: "⚠️ 2 more classes to fix ESE eligibility" },
  { label: "MAKAUT Credits Earned", value: "108 / 160", required: "On Track", met: true, note: "52 credits remaining for graduation" },
];

const TOP_RECRUITERS = [
  { name: "TCS", logo: "TCS", cgpa: 7.0, role: "System Engineer", package: "3.6 LPA", status: "eligible" as const },
  { name: "Wipro", logo: "WIP", cgpa: 7.0, role: "Project Engineer", package: "3.5 LPA", status: "eligible" as const },
  { name: "Capgemini", logo: "CAP", cgpa: 7.0, role: "Analyst", package: "4.0 LPA", status: "eligible" as const },
  { name: "Infosys", logo: "INF", cgpa: 6.5, role: "Systems Engineer", package: "3.6 LPA", status: "eligible" as const },
  { name: "Accenture", logo: "ACC", cgpa: 7.5, role: "ASE", package: "4.5 LPA", status: "eligible" as const },
  { name: "Amazon", logo: "AMZ", cgpa: 8.0, role: "SDE Intern", package: "10+ LPA", status: "eligible" as const },
];

const SKILL_GAPS = [
  { skill: "Data Structures & Algorithms", level: 65, priority: "high", tip: "Solve 2 LeetCode problems daily" },
  { skill: "SQL & Database Concepts", level: 80, priority: "medium", tip: "Strong — deepen query optimization" },
  { skill: "System Design Basics", level: 30, priority: "high", tip: "Start with Gaurav Sen YouTube series" },
  { skill: "OOPS in Java / C++", level: 70, priority: "medium", tip: "Review polymorphism & design patterns" },
  { skill: "OS Concepts", level: 55, priority: "medium", tip: "Focus on scheduling, deadlocks, paging" },
  { skill: "Communication Skills", level: 75, priority: "low", tip: "Join college Toastmasters club" },
];

export default function CareerPage() {
  const [activeTab, setActiveTab] = useState<"audit" | "placement">("audit");

  const cgpa = 8.21;
  const earnedCredits = 108;
  const totalCredits = 160;
  const creditPercent = Math.round((earnedCredits / totalCredits) * 100);
  const eligibleCount = PLACEMENT_ELIGIBILITY.filter((e) => e.met).length;
  const totalChecks = PLACEMENT_ELIGIBILITY.length;

  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Career & Degree Audit</h1>
            <p className="text-xs text-[#8A8F98] mt-0.5">
              B.Tech CSE · BCREC Autonomous ·{" "}
              <span className="text-white font-medium">3rd Year, Semester 5</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button size="md" variant="secondary" icon={<Download className="w-3.5 h-3.5 text-[#5E6AD2]" />}>
              Download Grade Sheet
            </Button>
            <Link href="/career/placements">
              <Button size="md" variant="primary" icon={<Briefcase className="w-3.5 h-3.5" />}>
                Placement Hub
              </Button>
            </Link>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 p-1 bg-[#0D0E10] border border-white/[0.08] rounded-lg w-fit">
          {[
            { key: "audit", label: "📊 Degree Audit" },
            { key: "placement", label: "🚀 Placement Readiness" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as "audit" | "placement")}
              className={`px-4 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === tab.key
                  ? "bg-[#1C1D22] text-white border border-white/[0.10] shadow-sm"
                  : "text-[#8A8F98] hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ======================== DEGREE AUDIT TAB ======================== */}
        {activeTab === "audit" && (
          <>
            {/* 3-Card Summary Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-4 space-y-1 bg-[#0D0E10] border-white/[0.08]">
                <div className="flex items-center justify-between text-xs text-[#8A8F98]">
                  <span>Cumulative CGPA</span>
                  <span className="text-emerald-400 font-mono font-semibold flex items-center gap-0.5">
                    <TrendingUp className="w-3 h-3" /> +0.12 vs Sem 3
                  </span>
                </div>
                <div className="text-3xl font-bold font-mono text-white">{cgpa}</div>
                <p className="text-[11px] text-[#8A8F98]">
                  Dept Rank:{" "}
                  <span className="font-mono text-white font-semibold">14 / 180</span> students
                </p>
              </Card>

              <Card className="p-4 space-y-1 bg-[#0D0E10] border-white/[0.08]">
                <div className="flex items-center justify-between text-xs text-[#8A8F98]">
                  <span>Degree Credits Earned</span>
                  <span className="text-indigo-300 font-mono font-semibold">{creditPercent}% Complete</span>
                </div>
                <div className="text-3xl font-bold font-mono text-white">
                  {earnedCredits}{" "}
                  <span className="text-sm text-[#8A8F98] font-normal">/ {totalCredits}</span>
                </div>
                <div className="w-full h-1.5 bg-white/[0.08] rounded-full overflow-hidden mt-1">
                  <div
                    className="h-full bg-indigo-500 rounded-full"
                    style={{ width: `${creditPercent}%` }}
                  />
                </div>
              </Card>

              <Card className="p-4 space-y-1 bg-[#0D0E10] border-white/[0.08]">
                <div className="flex items-center justify-between text-xs text-[#8A8F98]">
                  <span>Active Backlogs</span>
                  <span className="text-emerald-400 font-mono font-semibold">Clean Record</span>
                </div>
                <div className="text-3xl font-bold font-mono text-emerald-400">0</div>
                <p className="text-[11px] text-emerald-300 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Eligible for Autonomous Honors Degree
                </p>
              </Card>
            </div>

            {/* SGPA Chart + Honors Eligibility */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left: Semester Breakdown with Visual Bar */}
              <div className="lg:col-span-8 space-y-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-[#5E6AD2]" /> Semester-wise SGPA Progression
                </span>

                <Card className="p-5 bg-[#0D0E10] border-white/[0.08]">
                  {/* Bar Chart */}
                  <div className="flex items-end gap-4 h-28 mb-4">
                    {SEMESTERS.map((sem, idx) => {
                      const barHeight = ((sem.sgpa - 7) / 1.5) * 100;
                      return (
                        <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                          <span className="text-[10px] font-mono text-white font-bold">{sem.sgpa.toFixed(2)}</span>
                          <div
                            className={`w-full rounded-t-sm transition-all ${
                              sem.status === "current"
                                ? "bg-[#5E6AD2]"
                                : "bg-white/[0.15] hover:bg-white/[0.25]"
                            }`}
                            style={{ height: `${Math.max(barHeight, 20)}%` }}
                          />
                          <span
                            className={`text-[11px] font-mono ${
                              sem.status === "current" ? "text-[#5E6AD2] font-semibold" : "text-[#8A8F98]"
                            }`}
                          >
                            {sem.sem}
                          </span>
                          <span className="text-[10px] text-[#6E7480]">{sem.year}</span>
                        </div>
                      );
                    })}
                  </div>

                  {/* Table underneath */}
                  <div className="border-t border-white/[0.06] divide-y divide-white/[0.04]">
                    {SEMESTERS.map((sem, idx) => (
                      <div key={idx} className="py-2.5 flex items-center justify-between text-xs">
                        <div>
                          <span className="font-semibold text-white">{sem.sem}</span>
                          <span className="text-[#8A8F98] ml-2">{sem.credits} Credits · {sem.year}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span
                            className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                              sem.status === "current"
                                ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/25"
                                : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25"
                            }`}
                          >
                            {sem.status === "current" ? "In Progress" : "Passed ✓"}
                          </span>
                          <span className="font-bold font-mono text-white text-sm">{sem.sgpa.toFixed(2)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>

              {/* Right: Honors Eligibility + NPTEL */}
              <div className="lg:col-span-4 space-y-4">
                <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">
                    <Award className="w-4 h-4 text-amber-400" /> Honors Eligibility
                  </div>

                  <div className="space-y-2.5 text-xs">
                    <div className="flex items-center justify-between p-2.5 rounded bg-[#121316] border border-white/[0.04]">
                      <span className="text-[#ECEEF0]">Min CGPA: ≥ 8.00</span>
                      <span className="text-emerald-400 font-mono font-semibold">8.21 ✓</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 rounded bg-[#121316] border border-white/[0.04]">
                      <span className="text-[#ECEEF0]">No Backlogs Ever</span>
                      <span className="text-emerald-400 font-mono font-semibold">0 ✓</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 rounded bg-[#121316] border border-amber-500/20">
                      <span className="text-[#ECEEF0]">NPTEL Credits</span>
                      <span className="text-amber-300 font-mono font-semibold">4 / 8</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 rounded bg-[#121316] border border-rose-500/20">
                      <span className="text-[#ECEEF0]">DBMS Attendance</span>
                      <span className="text-rose-400 font-mono font-semibold">73.3% ✗</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-white/[0.06]">
                    <p className="text-[11px] text-[#8A8F98] leading-relaxed">
                      Fix DBMS attendance and complete 4 more NPTEL credits to secure Honors degree track.
                    </p>
                  </div>
                </Card>

                <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-2">
                  <span className="text-xs font-semibold text-[#8A8F98] uppercase tracking-wider flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-[#5E6AD2]" /> MOOC / NPTEL Progress
                  </span>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-[#ECEEF0]">Python for Data Science (NPTEL)</span>
                      <span className="text-emerald-400 font-mono text-[11px]">2 Credits ✓</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[#ECEEF0]">Cloud Computing (NPTEL)</span>
                      <span className="text-emerald-400 font-mono text-[11px]">2 Credits ✓</span>
                    </div>
                    <div className="flex items-center justify-between text-[#8A8F98]">
                      <span>DSA with C++ (Coursera)</span>
                      <span className="font-mono text-[11px] text-amber-300">In Progress</span>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          </>
        )}

        {/* ======================== PLACEMENT READINESS TAB ======================== */}
        {activeTab === "placement" && (
          <>
            {/* Placement Eligibility Banner */}
            <Card
              className={`p-4 border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                eligibleCount === totalChecks
                  ? "border-emerald-500/30 bg-gradient-to-r from-[#0D1410] to-[#0D0E10]"
                  : "border-amber-500/30 bg-gradient-to-r from-[#141008] to-[#0D0E10]"
              }`}
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2.5">
                  <span
                    className={`text-[11px] font-mono px-2.5 py-0.5 rounded font-semibold border flex items-center gap-1.5 ${
                      eligibleCount === totalChecks
                        ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                        : "bg-amber-500/15 text-amber-300 border-amber-500/30"
                    }`}
                  >
                    {eligibleCount === totalChecks ? (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : (
                      <AlertCircle className="w-3.5 h-3.5" />
                    )}
                    {eligibleCount}/{totalChecks} CRITERIA MET
                  </span>
                  <span className="text-sm font-semibold text-white">
                    {eligibleCount === totalChecks
                      ? "You are placement-eligible at BCREC T&P!"
                      : "Almost there — 1 criteria to fix"}
                  </span>
                </div>
                <p className="text-xs text-[#8A8F98]">
                  BCREC Training & Placement Cell pre-registration opens in{" "}
                  <span className="text-white font-semibold">February 2027</span>. Keep your DBMS attendance above 75%.
                </p>
              </div>
              <Link href="/plan">
                <Button size="sm" variant="secondary" icon={<ChevronRight className="w-3.5 h-3.5" />}>
                  Fix Now
                </Button>
              </Link>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left: Eligibility Checklist + Skill Gaps */}
              <div className="lg:col-span-7 space-y-5">
                {/* Eligibility Checklist */}
                <div className="space-y-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">
                    T&P Registration Eligibility Checklist
                  </span>
                  <Card className="overflow-hidden border-white/[0.08]">
                    <div className="divide-y divide-white/[0.04]">
                      {PLACEMENT_ELIGIBILITY.map((item, idx) => (
                        <div key={idx} className="p-3.5 flex items-start justify-between gap-3">
                          <div className="flex items-start gap-3">
                            {item.met ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                            ) : (
                              <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                            )}
                            <div>
                              <p className="text-xs font-semibold text-white">{item.label}</p>
                              <p className="text-[11px] text-[#8A8F98] mt-0.5">{item.note}</p>
                            </div>
                          </div>
                          <div className="text-right shrink-0">
                            <span
                              className={`text-xs font-mono font-bold ${
                                item.met ? "text-emerald-400" : "text-rose-400"
                              }`}
                            >
                              {item.value}
                            </span>
                            <span className="block text-[10px] text-[#8A8F98]">Need: {item.required}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>

                {/* Skill Gap Analysis */}
                <div className="space-y-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
                    <Code2 className="w-3.5 h-3.5 text-[#5E6AD2]" /> Technical Skill Readiness
                  </span>
                  <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3">
                    {SKILL_GAPS.map((skill, idx) => (
                      <div key={idx} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-white font-medium">{skill.skill}</span>
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                                skill.priority === "high"
                                  ? "bg-rose-500/15 text-rose-300"
                                  : skill.priority === "medium"
                                  ? "bg-amber-500/15 text-amber-300"
                                  : "bg-emerald-500/15 text-emerald-300"
                              }`}
                            >
                              {skill.priority === "high" ? "High Priority" : skill.priority === "medium" ? "Medium" : "Good"}
                            </span>
                            <span className="font-mono text-white font-semibold">{skill.level}%</span>
                          </div>
                        </div>
                        <div className="w-full h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              skill.level >= 75
                                ? "bg-emerald-500"
                                : skill.level >= 50
                                ? "bg-amber-500"
                                : "bg-rose-500"
                            }`}
                            style={{ width: `${skill.level}%` }}
                          />
                        </div>
                        <p className="text-[11px] text-[#8A8F98]">💡 {skill.tip}</p>
                      </div>
                    ))}
                  </Card>
                </div>
              </div>

              {/* Right: Top Recruiters + Timeline */}
              <div className="lg:col-span-5 space-y-5">
                {/* Top Recruiters */}
                <div className="space-y-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5 text-[#5E6AD2]" /> BCREC Top Recruiters
                  </span>
                  <Card className="overflow-hidden border-white/[0.08]">
                    <div className="divide-y divide-white/[0.04]">
                      {TOP_RECRUITERS.map((co, idx) => (
                        <div key={idx} className="p-3.5 flex items-center justify-between hover:bg-white/[0.02] transition-colors">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-md bg-white/[0.06] border border-white/[0.08] flex items-center justify-center text-[10px] font-mono font-bold text-[#5E6AD2]">
                              {co.logo}
                            </div>
                            <div>
                              <p className="text-xs font-semibold text-white">{co.name}</p>
                              <p className="text-[11px] text-[#8A8F98]">{co.role} · CGPA ≥ {co.cgpa}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <span className="text-xs font-mono font-bold text-emerald-400">{co.package}</span>
                            <span className="block text-[10px] text-emerald-300 flex items-center gap-0.5 justify-end">
                              <CheckCircle2 className="w-2.5 h-2.5" /> Eligible
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>

                {/* Placement Timeline */}
                <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
                    <Star className="w-3.5 h-3.5 text-amber-400" /> Placement Preparation Timeline
                  </span>
                  <div className="space-y-2.5 text-xs">
                    {[
                      { phase: "Now → Dec 2026", task: "Solve 150 LeetCode problems. Focus on Arrays, Strings, Trees.", status: "active" },
                      { phase: "Jan 2027", task: "NPTEL DSA certification. Resume preparation with T&P guidance.", status: "upcoming" },
                      { phase: "Feb 2027", task: "BCREC T&P pre-registration. Submit resume to portal.", status: "upcoming" },
                      { phase: "Mar–Apr 2027", task: "Mock interviews, Aptitude tests (Quantitative + Verbal + Technical).", status: "upcoming" },
                      { phase: "Jul–Aug 2027", task: "On-campus placement drives begin. 6th Sem final exams.", status: "future" },
                    ].map((item, idx) => (
                      <div key={idx} className="flex gap-3">
                        <div className="flex flex-col items-center pt-0.5">
                          <div
                            className={`w-2 h-2 rounded-full border shrink-0 ${
                              item.status === "active"
                                ? "bg-[#5E6AD2] border-[#5E6AD2]"
                                : item.status === "upcoming"
                                ? "bg-transparent border-white/[0.3]"
                                : "bg-transparent border-white/[0.1]"
                            }`}
                          />
                          {idx < 4 && <div className="w-px flex-1 bg-white/[0.06] mt-1 mb-0.5" style={{ minHeight: "16px" }} />}
                        </div>
                        <div className="pb-2">
                          <span
                            className={`text-[10px] font-mono font-semibold ${
                              item.status === "active" ? "text-[#5E6AD2]" : "text-[#6E7480]"
                            }`}
                          >
                            {item.phase}
                          </span>
                          <p className={`text-[11px] leading-relaxed mt-0.5 ${item.status === "active" ? "text-[#ECEEF0]" : "text-[#8A8F98]"}`}>
                            {item.task}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>

                {/* CTA */}
                <Card className="p-4 border-indigo-500/25 bg-gradient-to-br from-[#12131F] to-[#0D0E10] space-y-2">
                  <div className="flex items-center gap-2">
                    <Briefcase className="w-4 h-4 text-[#5E6AD2]" />
                    <span className="text-sm font-semibold text-white">Resume Checklist</span>
                  </div>
                  <p className="text-[11px] text-[#8A8F98] leading-relaxed">
                    Build your resume with CGPA, project highlights, NPTEL certifications, and internship experience.
                  </p>
                  <Link href="/career/placements">
                    <Button size="sm" variant="primary" icon={<ArrowUpRight className="w-3.5 h-3.5" />} className="w-full mt-1">
                      Open Full Placement Hub
                    </Button>
                  </Link>
                </Card>
              </div>
            </div>
          </>
        )}
      </div>
    </StudentLayout>
  );
}
