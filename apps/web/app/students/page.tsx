"use client";

import React, { useState } from "react";
import Link from "next/link";
import { WebLayout } from "@/components/layout/WebLayout";
import { Search } from "lucide-react";

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

export default function StudentsPage() {
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<"all" | "critical" | "warning" | "safe">("all");
  const [sortBy, setSortBy] = useState<"name" | "attendance" | "risk">("risk");

  const filteredStudents = STUDENTS.filter((student) => {
    const matchesSearch =
      student.name.toLowerCase().includes(search.toLowerCase()) ||
      student.rollNo.toLowerCase().includes(search.toLowerCase());
    const matchesRisk = riskFilter === "all" || student.attendanceRisk === riskFilter;
    return matchesSearch && matchesRisk;
  }).sort((a, b) => {
    if (sortBy === "name") return a.name.localeCompare(b.name);
    if (sortBy === "attendance") return a.attendance - b.attendance;
    const riskOrder = { critical: 0, warning: 1, safe: 2 };
    return riskOrder[a.attendanceRisk] - riskOrder[b.attendanceRisk];
  });

  const criticalCount = STUDENTS.filter((s) => s.attendanceRisk === "critical").length;
  const warningCount = STUDENTS.filter((s) => s.attendanceRisk === "warning").length;
  const safeCount = STUDENTS.filter((s) => s.attendanceRisk === "safe").length;

  return (
    <WebLayout>
      <div className="space-y-5 page-enter">
        {/* Header Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 border-b border-white/[0.08]">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold tracking-tight text-[#FFFFFF]">
                Student Directory
              </h1>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-white/[0.05] text-[#ECEEF0] border border-white/[0.10]">
                {STUDENTS.length} Tracked
              </span>
            </div>
            <p className="text-[13px] text-[#9DA3AE]">
              Deterministic attendance & academic progress across institutional cohorts
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="px-2.5 py-1 rounded-md bg-[#121316] border border-white/[0.08] text-rose-400 font-semibold">
              {criticalCount} Critical
            </span>
            <span className="px-2.5 py-1 rounded-md bg-[#121316] border border-white/[0.08] text-amber-400 font-semibold">
              {warningCount} Warning
            </span>
            <span className="px-2.5 py-1 rounded-md bg-[#121316] border border-white/[0.08] text-emerald-400 font-semibold">
              {safeCount} Safe
            </span>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-[#8A8F98] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter by student name or roll number..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-8 pl-8 pr-2.5 bg-[#121316] border border-white/[0.08] rounded-md text-[13px] text-[#FFFFFF] placeholder-[#6E7480] focus:outline-none focus:border-white/[0.2] transition-colors"
            />
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value as "all" | "critical" | "warning" | "safe")}
              className="h-8 px-2.5 bg-[#121316] border border-white/[0.08] rounded-md text-xs text-[#ECEEF0] focus:outline-none focus:border-white/[0.2] transition-colors"
            >
              <option value="all">All Risk Bands</option>
              <option value="critical">Critical (&lt; 75%)</option>
              <option value="warning">Warning (75–80%)</option>
              <option value="safe">Safe (&gt; 80%)</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as "name" | "attendance" | "risk")}
              className="h-8 px-2.5 bg-[#121316] border border-white/[0.08] rounded-md text-xs text-[#ECEEF0] focus:outline-none focus:border-white/[0.2] transition-colors"
            >
              <option value="risk">Sort by Risk</option>
              <option value="attendance">Sort by Attendance</option>
              <option value="name">Sort by Name</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="rounded-xl border border-white/[0.08] bg-[#121316] overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse" role="table">
              <thead>
                <tr className="border-b border-white/[0.08] bg-white/[0.02]">
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Student
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Roll Number
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Programme
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Attendance
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Assessment
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Tasks
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Mentor
                  </th>
                  <th className="py-3 px-4 text-right text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold pr-5">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {filteredStudents.map((student) => {
                  return (
                    <tr
                      key={student.id}
                      className="hover:bg-white/[0.03] transition-colors group"
                    >
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-sm text-[#FFFFFF] group-hover:text-white transition-colors">
                          {student.name}
                        </div>
                      </td>

                      <td className="py-2.5 px-3">
                        <code className="font-mono text-xs text-[#9DA3AE] bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.06]">
                          {student.rollNo}
                        </code>
                      </td>

                      <td className="py-2.5 px-3 text-sm text-[#ECEEF0]">
                        <span>{student.programme}</span>
                        <span className="text-[#8A8F98] ml-1.5 font-mono text-xs">
                          S{student.semester}
                        </span>
                      </td>

                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-2">
                          <span
                            className={`font-mono font-bold text-sm ${
                              student.attendance < 75
                                ? "text-rose-400"
                                : student.attendance < 80
                                ? "text-amber-400"
                                : "text-emerald-400"
                            }`}
                          >
                            {student.attendance}%
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded-md text-xs font-mono uppercase font-semibold ${
                              student.attendanceRisk === "critical"
                                ? "bg-rose-500/15 text-rose-400 border border-rose-500/25"
                                : student.attendanceRisk === "warning"
                                ? "bg-amber-500/15 text-amber-400 border border-amber-500/25"
                                : "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
                            }`}
                          >
                            {student.attendanceRisk}
                          </span>
                        </div>
                      </td>

                      <td className="py-2.5 px-3">
                        <span className="text-xs font-mono font-medium text-[#ECEEF0]">
                          {student.assessmentTrend === "improving"
                            ? "↑ Improving"
                            : student.assessmentTrend === "declining"
                            ? "↓ Declining"
                            : "→ Stable"}
                        </span>
                      </td>

                      <td className="py-2.5 px-3">
                        <span
                          className={`font-mono text-xs px-2 py-0.5 rounded-md ${
                            student.overdueTasks > 0
                              ? "bg-rose-500/15 text-rose-400 border border-rose-500/25 font-semibold"
                              : "text-[#8A8F98] bg-white/[0.03]"
                          }`}
                        >
                          {student.overdueTasks > 0
                            ? `${student.overdueTasks} overdue`
                            : "Clean"}
                        </span>
                      </td>

                      <td className="py-2.5 px-3 text-sm text-[#ECEEF0]">
                        {student.mentor}
                      </td>

                      <td className="py-2.5 px-3 pr-5 text-right">
                        <Link
                          href={`/students/${student.id}`}
                          className="h-7 px-2.5 text-xs font-medium rounded flex items-center text-[#FFFFFF] bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.08] transition-colors"
                        >
                          View
                        </Link>
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
