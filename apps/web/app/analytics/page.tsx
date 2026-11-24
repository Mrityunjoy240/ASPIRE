"use client";

import React from "react";
import { WebLayout } from "@/components/layout/WebLayout";

const ANALYTICS_DATA = {
  institution: {
    name: "BCREC",
    totalStudents: 2847,
    totalMentors: 89,
    criticalRisk: 234,
    warningRisk: 567,
    safeStudents: 2046,
  },
  attendanceTrends: [
    { month: "July", avgAttendance: 82.4, critical: 12, warning: 45 },
    { month: "August", avgAttendance: 79.8, critical: 28, warning: 67 },
    { month: "September", avgAttendance: 76.3, critical: 56, warning: 89 },
    { month: "October", avgAttendance: 74.1, critical: 89, warning: 112 },
  ],
  programmeBreakdown: [
    { name: "CSE (AIML)", students: 456, critical: 45, warning: 67, avgAttendance: 74.2 },
    { name: "Computer Science", students: 523, critical: 34, warning: 56, avgAttendance: 75.8 },
    { name: "Electronics & Comm.", students: 389, critical: 28, warning: 41, avgAttendance: 77.1 },
    { name: "Electrical Eng.", students: 298, critical: 22, warning: 34, avgAttendance: 78.5 },
    { name: "Mechanical Eng.", students: 412, critical: 31, warning: 48, avgAttendance: 76.3 },
    { name: "Civil Engineering", students: 345, critical: 27, warning: 39, avgAttendance: 77.8 },
    { name: "Information Tech.", students: 324, critical: 23, warning: 35, avgAttendance: 78.1 },
  ],
  assessmentTrends: [
    { component: "Continuous Assessment 1 (CIA-1)", avgScore: 68.4, trend: "stable", weight: "20%" },
    { component: "Continuous Assessment 2 (CIA-2)", avgScore: 71.2, trend: "improving", weight: "20%" },
    { component: "End Semester Exam (Projected)", avgScore: 65.8, trend: "declining", weight: "50%" },
    { component: "Laboratory Practical", avgScore: 78.9, trend: "improving", weight: "10%" },
  ],
  interventionStats: {
    totalCases: 234,
    open: 67,
    inReview: 34,
    planProposed: 28,
    pendingApproval: 12,
    active: 45,
    resolved: 48,
    escalated: 6,
  },
};

export default function AnalyticsPage() {
  return (
    <WebLayout>
      <div className="space-y-6 page-enter">
        {/* Header - Linear Style */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 border-b border-white/[0.08]">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold tracking-tight text-[#FFFFFF]">
                Institutional Risk Analytics
              </h1>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-white/[0.05] text-[#ECEEF0] border border-white/[0.10]">
                Real-time Aggregation
              </span>
            </div>
            <p className="text-[13px] text-[#9DA3AE]">
              Multi-cohort academic risk distribution, attendance decay trends, and intervention throughput
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <select className="h-8 px-2.5 bg-[#121316] border border-white/[0.08] rounded-md text-xs text-[#ECEEF0] focus:outline-none focus:border-white/[0.2] transition-colors">
              <option value="sem5">Current Semester (Sem 5)</option>
              <option value="90d">Past 90 Days</option>
              <option value="ay">Full Academic Year</option>
            </select>
            <button className="h-8 px-3 text-xs font-medium rounded-md bg-white/[0.04] hover:bg-white/[0.08] text-[#ECEEF0] border border-white/[0.08] transition-colors flex items-center">
              Export CSV
            </button>
          </div>
        </div>

        {/* 4 Top Metric Cards with High Contrast & Micro Animations */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
          <div className="p-4 rounded-xl bg-[#121316] border border-white/[0.08] hover:border-white/[0.16] transition-all duration-150 space-y-1.5">
            <div className="text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">Total Monitored</div>
            <div className="text-2xl font-bold font-mono text-[#FFFFFF] tracking-tight">
              {ANALYTICS_DATA.institution.totalStudents.toLocaleString()}
            </div>
            <div className="text-xs text-[#8A8F98] flex items-center gap-1.5">
              <span>7 B.Tech Departments</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#121316] border border-white/[0.08] hover:border-rose-500/30 transition-all duration-150 space-y-1.5 group">
            <div className="text-xs font-mono uppercase tracking-wider text-rose-400 font-semibold flex items-center justify-between">
              <span>Critical Risk (&lt; 75%)</span>
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400 linear-pulse-dot" />
            </div>
            <div className="text-2xl font-bold font-mono text-rose-400 tracking-tight">
              {ANALYTICS_DATA.institution.criticalRisk}
            </div>
            <div className="text-xs text-[#9DA3AE]">
              8.2% of cohort in detention danger
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#121316] border border-white/[0.08] hover:border-amber-500/30 transition-all duration-150 space-y-1.5">
            <div className="text-xs font-mono uppercase tracking-wider text-amber-400 font-semibold">
              Warning Watchlist (75–80%)
            </div>
            <div className="text-2xl font-bold font-mono text-amber-400 tracking-tight">
              {ANALYTICS_DATA.institution.warningRisk}
            </div>
            <div className="text-xs text-[#9DA3AE]">
              19.9% approaching threshold
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#121316] border border-white/[0.08] hover:border-emerald-500/30 transition-all duration-150 space-y-1.5">
            <div className="text-xs font-mono uppercase tracking-wider text-emerald-400 font-semibold">
              Safe & In Good Standing
            </div>
            <div className="text-2xl font-bold font-mono text-emerald-400 tracking-tight">
              {ANALYTICS_DATA.institution.safeStudents.toLocaleString()}
            </div>
            <div className="text-xs text-[#9DA3AE]">
              71.9% meet eligibility rules
            </div>
          </div>
        </div>

        {/* 2-Column Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Monthly Attendance Decay Tracker */}
          <div className="p-5 rounded-xl bg-[#121316] border border-white/[0.08] space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-[#FFFFFF] font-mono">
                  Attendance Trajectory
                </h2>
                <p className="text-xs text-[#9DA3AE] mt-0.5">Semester progression by month</p>
              </div>
              <span className="text-xs font-mono text-rose-400 font-semibold">
                -8.3% total decay
              </span>
            </div>

            <div className="space-y-3.5">
              {ANALYTICS_DATA.attendanceTrends.map((t) => (
                <div key={t.month} className="space-y-1.5 group">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-semibold text-[#ECEEF0]">{t.month}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-[#9DA3AE] text-xs">
                        <span className="text-rose-400 font-mono font-semibold">{t.critical}</span> crit ·{" "}
                        <span className="text-amber-400 font-mono font-semibold">{t.warning}</span> warn
                      </span>
                      <span className="font-mono font-bold text-[#FFFFFF] w-14 text-right">
                        {t.avgAttendance}%
                      </span>
                    </div>
                  </div>

                  <div className="w-full h-2.5 rounded-full bg-white/[0.06] overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        t.avgAttendance < 75
                          ? "bg-rose-500"
                          : t.avgAttendance < 80
                          ? "bg-amber-400"
                          : "bg-emerald-400"
                      }`}
                      style={{ width: `${t.avgAttendance}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Intervention Funnel Throughput */}
          <div className="p-5 rounded-xl bg-[#121316] border border-white/[0.08] space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-[#FFFFFF] font-mono">
                  Intervention Case Pipeline
                </h2>
                <p className="text-xs text-[#9DA3AE] mt-0.5">234 Total detected cases</p>
              </div>
              <span className="text-xs font-mono text-emerald-400 font-semibold">
                48 Resolved Successfully
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              {[
                { label: "OPEN CASES", val: ANALYTICS_DATA.interventionStats.open, border: "border-slate-500", text: "text-slate-200" },
                { label: "IN REVIEW", val: ANALYTICS_DATA.interventionStats.inReview, border: "border-[#5E6AD2]", text: "text-[#A5AEF6]" },
                { label: "PLAN PROPOSED", val: ANALYTICS_DATA.interventionStats.planProposed, border: "border-sky-400", text: "text-sky-400" },
                { label: "PENDING APPROVAL", val: ANALYTICS_DATA.interventionStats.pendingApproval, border: "border-amber-400", text: "text-amber-400" },
                { label: "ACTIVE INTERVENTIONS", val: ANALYTICS_DATA.interventionStats.active, border: "border-emerald-500", text: "text-emerald-400" },
                { label: "RESOLVED & RECOVERED", val: ANALYTICS_DATA.interventionStats.resolved, border: "border-emerald-600", text: "text-emerald-300" },
              ].map((s) => (
                <div key={s.label} className={`p-3 rounded-lg bg-white/[0.02] border-l-2 ${s.border}`}>
                  <div className="text-xs font-mono text-[#9DA3AE] truncate font-medium">{s.label}</div>
                  <div className={`text-xl font-bold font-mono ${s.text} mt-1`}>{s.val}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Department / Programme Breakdown Table */}
        <div className="rounded-xl border border-white/[0.08] bg-[#121316] overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-white/[0.08] flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-[#FFFFFF] font-mono">
              Department Cohort Vulnerability Breakdown
            </h2>
            <span className="text-xs font-mono text-[#9DA3AE]">Sorted by Risk % (DESC)</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse" role="table">
              <thead>
                <tr className="border-b border-white/[0.08] bg-white/[0.02]">
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Programme
                  </th>
                  <th className="py-3 px-4 text-right text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Enrolled
                  </th>
                  <th className="py-3 px-4 text-right text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Critical
                  </th>
                  <th className="py-3 px-4 text-right text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Warning
                  </th>
                  <th className="py-3 px-4 text-right text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Avg Attendance
                  </th>
                  <th className="py-3 px-4 text-right text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold pr-5">
                    Risk Ratio
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {ANALYTICS_DATA.programmeBreakdown.map((prog) => {
                  const riskRatio = (((prog.critical + prog.warning) / prog.students) * 100).toFixed(1);
                  return (
                    <tr key={prog.name} className="hover:bg-white/[0.03] transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-sm text-[#FFFFFF]">
                        {prog.name}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-sm text-[#ECEEF0]">
                        {prog.students}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-sm font-bold text-rose-400">
                        {prog.critical}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-sm font-bold text-amber-400">
                        {prog.warning}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-sm font-medium text-[#ECEEF0]">
                        {prog.avgAttendance}%
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-sm font-bold text-rose-400 pr-5">
                        {riskRatio}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </WebLayout>
  );
}
