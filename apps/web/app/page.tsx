"use client";

import React from "react";
import Link from "next/link";
import { WebLayout } from "@/components/layout/WebLayout";
import {
  AlertTriangle,
  Inbox,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  TrendingDown,
} from "lucide-react";
import { motion } from "motion/react";

const RECENT_CASES = [
  {
    id: "CAS-BCREC-2026-0042",
    student: "Ananya Sharma",
    roll: "BCREC-CS-2026-042",
    attendance: 73.3,
    status: "PENDING_APPROVAL",
    statusLabel: "Pending Approval",
    urgency: "URGENT",
    examInDays: 8,
    lastAction: "Today",
    isCritical: true,
  },
  {
    id: "CAS-BCREC-2026-0025",
    student: "Arjun Mehta",
    roll: "BCREC-ME-2026-042",
    attendance: 65.4,
    status: "ESCALATION_REQUIRED",
    statusLabel: "Escalated to HOD",
    urgency: "URGENT",
    examInDays: 3,
    lastAction: "5d ago",
    isCritical: true,
  },
  {
    id: "CAS-BCREC-2026-0038",
    student: "Rohit Kumar",
    roll: "BCREC-CS-2026-018",
    attendance: 68.5,
    status: "PLAN_PROPOSED",
    statusLabel: "Plan Proposed",
    urgency: "URGENT",
    examInDays: 12,
    lastAction: "1d ago",
    isCritical: true,
  },
  {
    id: "CAS-BCREC-2026-0031",
    student: "Vikram Patel",
    roll: "BCREC-EE-2026-007",
    attendance: 76.8,
    status: "OPEN",
    statusLabel: "Open",
    urgency: "ATTENTION",
    examInDays: 5,
    lastAction: "3d ago",
    isCritical: false,
  },
  {
    id: "CAS-BCREC-2026-0035",
    student: "Priya Singh",
    roll: "BCREC-CS-2026-029",
    attendance: 78.2,
    status: "IN_REVIEW",
    statusLabel: "In Review",
    urgency: "ATTENTION",
    examInDays: 15,
    lastAction: "2d ago",
    isCritical: false,
  },
];

export default function HomePage() {
  return (
    <WebLayout>
      <div className="space-y-8 page-enter">
        {/* Hero Section — Balanced Mid Density */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-5 border-b border-white/[0.08]">
          <div className="space-y-1.5 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.09] text-xs text-[#9DA3AE]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#5E6AD2] linear-pulse-dot" />
              <span className="font-medium text-[#ECEEF0]">Academic Intelligence Platform</span>
              <span className="text-[#6E7480]">/</span>
              <span className="text-[#FFFFFF] font-mono font-semibold">P0 Target Demo</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#FFFFFF]">
              Student Success Command Center
            </h1>
            <p className="text-[13px] text-[#9DA3AE] leading-relaxed">
              Deterministic rule engines calculate attendance & eligibility. Autonomous specialists propose interventions. Mentors verify and approve.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-shrink-0">
            <Link
              href="/queue"
              className="h-8 px-3 text-[13px] font-medium bg-[#FFFFFF] hover:bg-white/90 text-[#08090A] rounded-md transition-all active:scale-[0.98] flex items-center gap-2 shadow-sm"
            >
              <span>Review Triage Queue</span>
              <span className="px-1.5 py-0.2 rounded-full bg-black/10 font-mono text-[11px] font-bold">
                10
              </span>
            </Link>
            <Link
              href="/students"
              className="h-8 px-3 text-[13px] font-medium bg-white/[0.04] hover:bg-white/[0.08] text-[#ECEEF0] border border-white/[0.09] rounded-md transition-colors flex items-center"
            >
              All Students Directory
            </Link>
          </div>
        </div>

        {/* Priority Action Cards — Mid Density */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          <motion.div whileHover={{ y: -2 }} transition={{ duration: 0.15 }} className="h-full">
            <Link
              href="/queue"
              className="p-4 rounded-xl bg-[#121316] border border-white/[0.08] hover:border-rose-500/35 transition-all group flex flex-col justify-between h-full space-y-2.5"
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                    <span className="text-[11px] font-mono text-rose-400 uppercase tracking-wider font-semibold">
                      Critical Triage
                    </span>
                  </div>
                  <span className="text-[11px] font-mono font-bold text-rose-400 px-2 py-0.5 rounded bg-rose-500/15 border border-rose-500/25">
                    10 Students
                  </span>
                </div>
                <p className="text-sm font-semibold text-[#FFFFFF]">
                  Immediate attention required
                </p>
                <p className="text-[13px] text-[#9DA3AE] leading-relaxed">
                  Attendance below institutional 75% threshold with upcoming End Semester Examinations.
                </p>
              </div>
              <div className="pt-1.5 flex items-center gap-1.5 text-xs font-medium text-rose-400 group-hover:translate-x-1 transition-transform">
                <span>Open triage queue</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </div>
            </Link>
          </motion.div>

          <motion.div whileHover={{ y: -2 }} transition={{ duration: 0.15 }} className="h-full">
            <Link
              href="/queue"
              className="p-4 rounded-xl bg-[#121316] border border-white/[0.08] hover:border-[#5E6AD2]/40 transition-all group flex flex-col justify-between h-full space-y-2.5"
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Inbox className="w-3.5 h-3.5 text-[#5E6AD2]" />
                    <span className="text-[11px] font-mono text-[#A5AEF6] uppercase tracking-wider font-semibold">
                      Plan Approvals
                    </span>
                  </div>
                  <span className="text-[11px] font-mono font-bold text-[#A5AEF6] px-2 py-0.5 rounded bg-[#5E6AD2]/15 border border-[#5E6AD2]/30">
                    3 Ready
                  </span>
                </div>
                <p className="text-sm font-semibold text-[#FFFFFF]">
                  Intervention plans awaiting sign-off
                </p>
                <p className="text-[13px] text-[#9DA3AE] leading-relaxed">
                  Recovery actions accepted by students. One-click mentor verification required to activate.
                </p>
              </div>
              <div className="pt-1.5 flex items-center gap-1.5 text-xs font-medium text-[#A5AEF6] group-hover:translate-x-1 transition-transform">
                <span>Review proposed plans</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </div>
            </Link>
          </motion.div>

          <motion.div whileHover={{ y: -2 }} transition={{ duration: 0.15 }} className="h-full">
            <div className="p-4 rounded-xl bg-[#121316] border border-white/[0.08] flex flex-col justify-between h-full space-y-2.5">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-[11px] font-mono text-emerald-400 uppercase tracking-wider font-semibold">
                      Rule Verification
                    </span>
                  </div>
                  <span className="text-[11px] font-mono font-bold text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/25">
                    100% Deterministic
                  </span>
                </div>
                <p className="text-sm font-semibold text-[#FFFFFF]">
                  Calculations Verified Safe
                </p>
                <p className="text-[13px] text-[#9DA3AE] leading-relaxed">
                  All attendance & eligibility math generated strictly via pure Python engines without AI hallucination.
                </p>
              </div>
              <div className="pt-1.5 flex items-center gap-1.5 text-xs font-medium text-emerald-400">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Non-repudiable audit log active</span>
              </div>
            </div>
          </motion.div>
        </div>

        {/* 2-Column Split View */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Workload Column (2/3) */}
          <div className="lg:col-span-2 space-y-6">
            <div className="rounded-xl border border-white/[0.08] bg-[#121316] overflow-hidden shadow-sm">
              <div className="px-4 py-3 border-b border-white/[0.08] flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-[#FFFFFF] uppercase tracking-wider font-mono">
                    Urgent Cases Queue (DM-SS03)
                  </h2>
                  <p className="text-sm text-[#9DA3AE] mt-0.5">
                    Ranked by Urgency Band → Exam Proximity → Days Since Last Action
                  </p>
                </div>
                <Link
                  href="/queue"
                  className="text-sm font-medium text-[#A5AEF6] hover:text-[#FFFFFF] transition-colors flex items-center gap-1.5"
                >
                  <span>Open full queue</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>

              <div className="divide-y divide-white/[0.06]">
                {RECENT_CASES.map((c) => (
                  <div
                    key={c.id}
                    className="p-4 hover:bg-white/[0.02] transition-colors flex items-center justify-between gap-4"
                  >
                    <div className="flex-1 min-w-0 space-y-1.5">
                      <div className="flex items-center gap-2.5">
                        <span className="text-sm font-semibold text-[#FFFFFF] truncate">
                          {c.student}
                        </span>
                        <code className="text-xs font-mono text-[#9DA3AE] bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.06]">
                          {c.roll}
                        </code>
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-mono font-semibold ${
                            c.urgency === "URGENT"
                              ? "bg-rose-500/15 text-rose-400 border border-rose-500/25"
                              : "bg-amber-500/15 text-amber-400 border border-amber-500/25"
                          }`}
                        >
                          {c.urgency}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-[#9DA3AE]">
                        <span className="flex items-center gap-1.5">
                          <TrendingDown className="w-4 h-4 text-rose-400" />
                          <span>Attendance:</span>
                          <span
                            className={`font-mono font-bold ${
                              c.attendance < 75
                                ? "text-rose-400"
                                : "text-amber-400"
                            }`}
                          >
                            {c.attendance}%
                          </span>
                          <span className="text-[#6E7480]">/ 75% min</span>
                        </span>
                        <span>•</span>
                        <span>
                          Exam:{" "}
                          <span className="font-mono text-[#FFFFFF] font-semibold">
                            {c.examInDays} days
                          </span>
                        </span>
                        <span>•</span>
                        <span className="text-[#8A8F98]">
                          Active: {c.lastAction}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span
                        className={`px-2.5 py-1 rounded-md text-xs font-mono font-medium ${
                          c.status === "PENDING_APPROVAL"
                            ? "bg-[#5E6AD2]/20 text-[#A5AEF6] border border-[#5E6AD2]/35"
                            : c.status === "ESCALATION_REQUIRED"
                            ? "bg-rose-500/20 text-rose-400 border border-rose-500/35"
                            : "bg-white/[0.05] text-[#ECEEF0] border border-white/[0.08]"
                        }`}
                      >
                        {c.statusLabel}
                      </span>
                      <Link
                        href="/queue"
                        className="h-7 px-2.5 text-xs font-medium text-[#FFFFFF] bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.08] rounded transition-colors flex items-center"
                      >
                        Review
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Loop Steps with Balanced Padding */}
            <div className="p-4 rounded-xl border border-white/[0.08] bg-[#121316] space-y-3.5">
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-[#FFFFFF] font-mono">
                    Autonomous Intelligence Cycle
                  </h3>
                  <p className="text-sm text-[#9DA3AE] mt-0.5">End-to-end closed-loop student intervention architecture</p>
                </div>
                <span className="text-xs font-mono text-emerald-400 flex items-center gap-1.5 font-semibold">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 linear-pulse-dot" />
                  Active Loop
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 text-center">
                {[
                  { step: "OBSERVE", sub: "Data Feed" },
                  { step: "UNDERSTAND", sub: "Syllabus" },
                  { step: "DETECT", sub: "Risk Signals" },
                  { step: "PLAN", sub: "AI Recovery" },
                  { step: "ASSIST", sub: "Study Tasks" },
                  { step: "VERIFY", sub: "Improvement" },
                  { step: "REPLAN", sub: "Adaptation" },
                  { step: "ESCALATE", sub: "HOD / CT" },
                ].map((item, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05] hover:border-white/[0.15] transition-colors"
                  >
                    <div className="text-xs font-mono font-bold text-[#FFFFFF]">
                      {item.step}
                    </div>
                    <div className="text-xs text-[#9DA3AE] mt-1 truncate">
                      {item.sub}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column (1/3) */}
          <div className="space-y-6">
            {/* Attendance Distribution Card */}
            <div className="p-4 rounded-xl border border-white/[0.08] bg-[#121316] space-y-3.5">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-[#FFFFFF] font-mono">
                  Cohort Attendance Health
                </h3>
                <p className="text-sm text-[#9DA3AE] mt-0.5">
                  2,847 Students · BCREC Reference Batch
                </p>
              </div>

              {/* High Visibility Distribution Bar */}
              <div className="w-full h-3 rounded-full bg-white/[0.06] overflow-hidden flex">
                <div style={{ width: "8.2%" }} className="bg-rose-500" title="Critical: 234" />
                <div style={{ width: "19.9%" }} className="bg-amber-400" title="Warning: 567" />
                <div style={{ width: "71.9%" }} className="bg-emerald-400" title="Safe: 2,046" />
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <div className="flex items-center gap-2.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-400" />
                    <span className="text-[#ECEEF0] font-medium">Critical (&lt; 75%)</span>
                  </div>
                  <span className="font-mono font-bold text-rose-400 text-sm">234</span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <div className="flex items-center gap-2.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                    <span className="text-[#ECEEF0] font-medium">Watchlist (75–80%)</span>
                  </div>
                  <span className="font-mono font-bold text-amber-400 text-sm">567</span>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <div className="flex items-center gap-2.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                    <span className="text-[#ECEEF0] font-medium">In Good Standing</span>
                  </div>
                  <span className="font-mono font-bold text-emerald-400 text-sm">2,046</span>
                </div>
              </div>
            </div>

            {/* Pipeline Stage Counts */}
            <div className="p-4 rounded-xl border border-white/[0.08] bg-[#121316] space-y-3.5">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-[#FFFFFF] font-mono">
                Intervention Lifecycle
              </h3>

              <div className="space-y-1.5">
                {[
                  { label: "OPEN CASES", count: 67 },
                  { label: "IN REVIEW", count: 34 },
                  { label: "PLAN PROPOSED", count: 28 },
                  { label: "PENDING APPROVAL", count: 12 },
                  { label: "ACTIVE CASES", count: 45 },
                  { label: "RESOLVED RECOVERY", count: 48 },
                  { label: "ESCALATED TO HOD", count: 6 },
                ].map((p) => (
                  <div
                    key={p.label}
                    className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] transition-colors border border-white/[0.04]"
                  >
                    <span className="text-[#9DA3AE] font-mono text-xs font-medium">{p.label}</span>
                    <span className="font-mono font-bold text-[#FFFFFF] text-sm">{p.count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </WebLayout>
  );
}
