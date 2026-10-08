"use client";

import React, { useState } from "react";
import { WebLayout } from "@/components/layout/WebLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";

const STUDENTS = [
  {
    id: "STU-001",
    name: "Ananya Sharma",
    rollNo: "BCREC-CS-2026-042",
    batch: "2026-2030",
    programme: "B.Tech CSE (AIML)",
    semester: 5,
    attendance: 73.3,
    attendanceRisk: "critical" as const,
    assessmentTrend: "declining",
    overdueTasks: 2,
    mentor: "Dr. A. Sen",
    status: "ACTIVE",
  },
  {
    id: "STU-002",
    name: "Rohit Kumar",
    rollNo: "BCREC-CS-2026-018",
    batch: "2026-2030",
    programme: "B.Tech CSE (AIML)",
    semester: 5,
    attendance: 68.5,
    attendanceRisk: "critical" as const,
    assessmentTrend: "stable",
    overdueTasks: 3,
    mentor: "Dr. A. Sen",
    status: "ACTIVE",
  },
  {
    id: "STU-003",
    name: "Priya Singh",
    rollNo: "BCREC-CS-2026-029",
    batch: "2026-2030",
    programme: "B.Tech CSE (AIML)",
    semester: 5,
    attendance: 78.2,
    attendanceRisk: "warning" as const,
    assessmentTrend: "declining",
    overdueTasks: 1,
    mentor: "Dr. R. Gupta",
    status: "ACTIVE",
  },
  {
    id: "STU-004",
    name: "Vikram Patel",
    rollNo: "BCREC-EE-2026-007",
    batch: "2026-2030",
    programme: "B.Tech EE",
    semester: 5,
    attendance: 76.8,
    attendanceRisk: "warning" as const,
    assessmentTrend: "stable",
    overdueTasks: 0,
    mentor: "Prof. S. Das",
    status: "ACTIVE",
  },
  {
    id: "STU-005",
    name: "Sneha Reddy",
    rollNo: "BCREC-CS-2026-011",
    batch: "2026-2030",
    programme: "B.Tech CSE (AIML)",
    semester: 5,
    attendance: 82.1,
    attendanceRisk: "safe" as const,
    assessmentTrend: "improving",
    overdueTasks: 0,
    mentor: "Dr. R. Gupta",
    status: "ACTIVE",
  },
  {
    id: "STU-006",
    name: "Arjun Mehta",
    rollNo: "BCREC-ME-2026-042",
    batch: "2026-2030",
    programme: "B.Tech ME",
    semester: 5,
    attendance: 65.4,
    attendanceRisk: "critical" as const,
    assessmentTrend: "declining",
    overdueTasks: 4,
    mentor: "Prof. S. Das",
    status: "ACTIVE",
  },
  {
    id: "STU-007",
    name: "Kavya Nair",
    rollNo: "BCREC-CS-2026-033",
    batch: "2026-2030",
    programme: "B.Tech CSE (AIML)",
    semester: 5,
    attendance: 79.5,
    attendanceRisk: "warning" as const,
    assessmentTrend: "stable",
    overdueTasks: 1,
    mentor: "Dr. R. Gupta",
    status: "ACTIVE",
  },
  {
    id: "STU-008",
    name: "Rahul Verma",
    rollNo: "BCREC-EC-2026-019",
    batch: "2026-2030",
    programme: "B.Tech ECE",
    semester: 5,
    attendance: 85.3,
    attendanceRisk: "safe" as const,
    assessmentTrend: "improving",
    overdueTasks: 0,
    mentor: "Dr. K. Iyer",
    status: "ACTIVE",
  },
];

function getRiskVariant(risk: string) {
  switch (risk) {
    case "critical": return "critical";
    case "warning": return "warning";
    default: return "safe";
  }
}

function getTrendBadge(trend: string) {
  switch (trend) {
    case "improving": return <StatusBadge variant="safe" showPulse={false}>↑ Improving</StatusBadge>;
    case "stable": return <StatusBadge variant="safe" showPulse={false}>→ Stable</StatusBadge>;
    case "declining": return <StatusBadge variant="warning" showPulse={true}>↓ Declining</StatusBadge>;
    default: return <StatusBadge variant="safe" showPulse={false}>—</StatusBadge>;
  }
}

export default function StudentsPage() {
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<"all" | "critical" | "warning" | "safe">("all");
  const [sortBy, setSortBy] = useState<"name" | "attendance" | "risk">("risk");

  const filteredStudents = STUDENTS.filter((student) => {
    const matchesSearch = student.name.toLowerCase().includes(search.toLowerCase()) ||
      student.rollNo.toLowerCase().includes(search.toLowerCase());
    const matchesRisk = riskFilter === "all" || student.attendanceRisk === riskFilter;
    return matchesSearch && matchesRisk;
  }).sort((a, b) => {
    if (sortBy === "name") return a.name.localeCompare(b.name);
    if (sortBy === "attendance") return a.attendance - b.attendance;
    const riskOrder = { critical: 0, warning: 1, safe: 2 };
    return riskOrder[a.attendanceRisk] - riskOrder[b.attendanceRisk];
  });

  const criticalCount = STUDENTS.filter(s => s.attendanceRisk === "critical").length;
  const warningCount = STUDENTS.filter(s => s.attendanceRisk === "warning").length;
  const safeCount = STUDENTS.filter(s => s.attendanceRisk === "safe").length;

  return (
    <WebLayout>
      <div className="space-y-6 animate-fade-in">
        {/* Header with Metrics */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 mb-6">
          <div>
            <h1 className="text-page-title">Students</h1>
            <p className="text-body text-slate-400 mt-1">Monitor student risk signals across all programmes</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <div className="glass-card px-4 py-3">
              <div className="text-2xl font-extrabold font-mono text-rose-400">{criticalCount}</div>
              <div className="text-micro text-slate-500">Critical Risk</div>
            </div>
            <div className="glass-card px-4 py-3">
              <div className="text-2xl font-extrabold font-mono text-amber-400">{warningCount}</div>
              <div className="text-micro text-slate-500">Warning</div>
            </div>
            <div className="glass-card px-4 py-3">
              <div className="text-2xl font-extrabold font-mono text-emerald-400">{safeCount}</div>
              <div className="text-micro text-slate-500">Safe</div>
            </div>
            <div className="glass-card px-4 py-3">
              <div className="text-2xl font-extrabold font-mono text-indigo-400">{STUDENTS.length}</div>
              <div className="text-micro text-slate-500">Total</div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <div className="flex flex-col lg:flex-row lg:items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder="Search by name or roll number..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value as "all" | "critical" | "warning" | "safe")}
                className="px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none focus:border-indigo-500/50"
              >
                <option value="all">All Risk Levels</option>
                <option value="critical">Critical Only</option>
                <option value="warning">Warning Only</option>
                <option value="safe">Safe Only</option>
              </select>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as "name" | "attendance" | "risk")}
                className="px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none focus:border-indigo-500/50"
              >
                <option value="risk">Sort by Risk</option>
                <option value="name">Sort by Name</option>
                <option value="attendance">Sort by Attendance</option>
              </select>
            </div>
          </div>
        </Card>

        {/* Student Table */}
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full" role="table">
              <thead>
                <tr className="border-b border-white/[0.08]">
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Student</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Roll No</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Programme</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Attendance</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Risk</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Assessment</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Overdue</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Mentor</th>
                  <th className="px-4 py-3 text-right text-micro text-slate-500 uppercase tracking-wider font-semibold pr-4">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {filteredStudents.map((student) => (
                  <tr key={student.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-4">
                      <div>
                        <p className="font-semibold text-white">{student.name}</p>
                        <p className="text-micro text-slate-500">Batch {student.batch} · Sem {student.semester}</p>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <code className="font-mono text-slate-300">{student.rollNo}</code>
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-sm text-slate-300 truncate max-w-xs">{student.programme}</p>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-2">
                        <span className={`font-mono font-bold ${student.attendance < 75 ? "text-rose-400" : student.attendance < 80 ? "text-amber-400" : "text-emerald-400"}`}>
                          {student.attendance}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge variant={getRiskVariant(student.attendanceRisk)} showPulse={student.attendanceRisk === "critical"}>
                        {student.attendanceRisk.toUpperCase()}
                      </StatusBadge>
                    </td>
                    <td className="px-4 py-4">
                      {getTrendBadge(student.assessmentTrend)}
                    </td>
                    <td className="px-4 py-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-semibold ${
                        student.overdueTasks > 0 ? "text-rose-400 bg-rose-500/10 border-rose-500/30 border" :
                        "text-emerald-400 bg-emerald-500/10 border-emerald-500/30 border"
                      }`}>
                        {student.overdueTasks} overdue
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-sm text-slate-300">{student.mentor}</p>
                    </td>
                    <td className="px-4 py-4 pr-4">
                      <div className="flex items-center gap-2 justify-end">
                        <Button size="sm" variant="ghost" onClick={() => console.log("View", student.id)}>
                          View
                        </Button>
                        <Button size="sm" variant="primary" onClick={() => console.log("Plan", student.id)}>
                          Plan
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </WebLayout>
  );
}