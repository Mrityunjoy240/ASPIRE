"use client";

import React from "react";
import { WebLayout } from "@/components/layout/WebLayout";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";

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
    { month: "Jul", avgAttendance: 82.4, critical: 12, warning: 45 },
    { month: "Aug", avgAttendance: 79.8, critical: 28, warning: 67 },
    { month: "Sep", avgAttendance: 76.3, critical: 56, warning: 89 },
    { month: "Oct", avgAttendance: 74.1, critical: 89, warning: 112 },
  ],
  programmeBreakdown: [
    { name: "CSE (AIML)", students: 456, critical: 45, warning: 67, avgAttendance: 74.2 },
    { name: "CSE", students: 523, critical: 34, warning: 56, avgAttendance: 75.8 },
    { name: "ECE", students: 389, critical: 28, warning: 41, avgAttendance: 77.1 },
    { name: "EE", students: 298, critical: 22, warning: 34, avgAttendance: 78.5 },
    { name: "ME", students: 412, critical: 31, warning: 48, avgAttendance: 76.3 },
    { name: "CE", students: 345, critical: 27, warning: 39, avgAttendance: 77.8 },
    { name: "IT", students: 324, critical: 23, warning: 35, avgAttendance: 78.1 },
  ],
  assessmentTrends: [
    { component: "CIA-1", avgScore: 68.4, trend: "stable" },
    { component: "CIA-2", avgScore: 71.2, trend: "improving" },
    { component: "ESE (Projected)", avgScore: 65.8, trend: "declining" },
    { component: "Lab", avgScore: 78.9, trend: "improving" },
    { component: "Assignments", avgScore: 72.3, trend: "stable" },
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
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <header className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 mb-6">
          <div>
            <h1 className="text-page-title">Analytics</h1>
            <p className="text-body text-slate-400 mt-1">Institution-wide risk intelligence & trends</p>
          </div>
          <div className="flex gap-3">
            <select className="px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none focus:border-indigo-500/50">
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="semester">Current Semester</option>
              <option value="year">Academic Year</option>
            </select>
            <Button variant="secondary">Export Report</Button>
          </div>
        </header>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-micro text-slate-500">Total Students</p>
                <p className="text-3xl font-extrabold font-mono text-white">{ANALYTICS_DATA.institution.totalStudents.toLocaleString()}</p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-indigo-400">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                </svg>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-micro text-slate-500">Critical Risk</p>
                <p className="text-3xl font-extrabold font-mono text-rose-400">{ANALYTICS_DATA.institution.criticalRisk}</p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-rose-500/20 flex items-center justify-center border border-rose-500/30">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-rose-400">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-micro text-slate-500">Warning Risk</p>
                <p className="text-3xl font-extrabold font-mono text-amber-400">{ANALYTICS_DATA.institution.warningRisk}</p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center border border-amber-500/30">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-amber-400">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-micro text-slate-500">Safe Students</p>
                <p className="text-3xl font-extrabold font-mono text-emerald-400">{ANALYTICS_DATA.institution.safeStudents}</p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center border border-emerald-500/30">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-emerald-400">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
            </div>
          </Card>
        </div>

        {/* Charts Section */}
        <div className="grid lg:grid-cols-2 gap-6 mb-6">
          {/* Attendance Trend */}
          <Card className="lg:col-span-2">
            <h3 className="text-section-heading mb-4">Attendance Trend (Semester)</h3>
            <div className="space-y-4">
              {ANALYTICS_DATA.attendanceTrends.map((month) => (
                <div key={month.month} className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <span className="font-semibold text-white w-20">{month.month}</span>
                      <div className="flex-1 h-2 bg-white/[0.08] rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500" style={{ width: `${month.avgAttendance}%` }} />
                      </div>
                    </div>
                    <div className="flex items-center gap-6 text-sm">
                      <span className="font-mono font-bold text-white">{month.avgAttendance}%</span>
                      <StatusBadge variant="critical" showPulse={false}>{month.critical} Critical</StatusBadge>
                      <StatusBadge variant="warning" showPulse={false}>{month.warning} Warning</StatusBadge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Programme Breakdown */}
          <Card className="lg:col-span-2">
            <h3 className="text-section-heading mb-4">Programme Risk Breakdown</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/[0.08]">
                    <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Programme</th>
                    <th className="px-4 py-3 text-right text-micro text-slate-500 uppercase tracking-wider font-semibold">Students</th>
                    <th className="px-4 py-3 text-right text-micro text-slate-500 uppercase tracking-wider font-semibold">Critical</th>
                    <th className="px-4 py-3 text-right text-micro text-slate-500 uppercase tracking-wider font-semibold">Warning</th>
                    <th className="px-4 py-3 text-right text-micro text-slate-500 uppercase tracking-wider font-semibold">Avg Attendance</th>
                    <th className="px-4 py-3 text-right text-micro text-slate-500 uppercase tracking-wider font-semibold">Risk %</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {ANALYTICS_DATA.programmeBreakdown.map((prog) => (
                    <tr key={prog.name} className="hover:bg-white/[0.02]">
                      <td className="px-4 py-3">
                        <p className="font-medium text-white">{prog.name}</p>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-slate-300">{prog.students}</td>
                      <td className="px-4 py-3 text-right font-mono text-rose-400">{prog.critical}</td>
                      <td className="px-4 py-3 text-right font-mono text-amber-400">{prog.warning}</td>
                      <td className="px-4 py-3 text-right font-mono font-bold text-white">{prog.avgAttendance}%</td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-mono text-rose-400">{(((prog.critical + prog.warning) / prog.students) * 100).toFixed(1)}%</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* Assessment Trends & Intervention Stats */}
        <div className="grid lg:grid-cols-2 gap-6">
          <Card>
            <h3 className="text-section-heading mb-4">Assessment Component Trends</h3>
            <div className="space-y-3">
              {ANALYTICS_DATA.assessmentTrends.map((comp) => (
                <div key={comp.component} className="flex items-center justify-between p-3 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-white">{comp.component}</span>
                    <StatusBadge variant={comp.trend === "improving" ? "safe" : comp.trend === "declining" ? "warning" : "safe"} showPulse={false}>
                      {comp.trend === "improving" ? "^ Improving" : comp.trend === "declining" ? "v Declining" : "-> Stable"}
                    </StatusBadge>
                  </div>
                  <span className="font-mono font-bold text-white text-lg">{comp.avgScore}%</span>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <h3 className="text-section-heading mb-4">Intervention Pipeline</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                <p className="text-micro text-slate-500">Total Cases</p>
                <p className="text-3xl font-extrabold font-mono text-white">{ANALYTICS_DATA.interventionStats.totalCases}</p>
              </div>
              <div className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                <p className="text-micro text-slate-500">Open</p>
                <p className="text-2xl font-extrabold font-mono text-rose-400">{ANALYTICS_DATA.interventionStats.open}</p>
              </div>
              <div className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                <p className="text-micro text-slate-500">In Review</p>
                <p className="text-2xl font-extrabold font-mono text-amber-400">{ANALYTICS_DATA.interventionStats.inReview}</p>
              </div>
              <div className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                <p className="text-micro text-slate-500">Plan Proposed</p>
                <p className="text-2xl font-extrabold font-mono text-sky-400">{ANALYTICS_DATA.interventionStats.planProposed}</p>
              </div>
              <div className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                <p className="text-micro text-slate-500">Pending Approval</p>
                <p className="text-2xl font-extrabold font-mono text-sky-400">{ANALYTICS_DATA.interventionStats.pendingApproval}</p>
              </div>
              <div className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                <p className="text-micro text-slate-500">Active</p>
                <p className="text-2xl font-extrabold font-mono text-emerald-400">{ANALYTICS_DATA.interventionStats.active}</p>
              </div>
              <div className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                <p className="text-micro text-slate-500">Resolved</p>
                <p className="text-2xl font-extrabold font-mono text-emerald-400">{ANALYTICS_DATA.interventionStats.resolved}</p>
              </div>
              <div className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                <p className="text-micro text-slate-500">Escalated</p>
                <p className="text-2xl font-extrabold font-mono text-rose-400">{ANALYTICS_DATA.interventionStats.escalated}</p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </WebLayout>
  );
}