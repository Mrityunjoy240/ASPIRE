"use client";

import React, { useState } from "react";
import Link from "next/link";
import { WebLayout } from "@/components/layout/WebLayout";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Clock,
  BookOpen,
  FileCheck,
  ListTodo,
} from "lucide-react";

const STUDENT_DATA = {
  id: "STU-001",
  name: "Ananya Sharma",
  rollNo: "BCREC-CS-2026-042",
  batch: "2026-2030",
  programme: "B.Tech CSE (AIML)",
  semester: 5,
  email: "ananya.sharma@bcrec.ac.in",
  mentor: "Dr. A. Sen",
  classTeacher: "Prof. R. Gupta",
  attendance: 73.3,
  attendanceRisk: "critical" as const,
  assessmentTrend: "declining",
  overdueTasks: 2,
  courses: [
    { id: "cs501", name: "Database Management Systems", code: "CS501", conducted: 30, attended: 22, threshold: 75, trend: "declining" },
    { id: "cs502", name: "Computer Networks", code: "CS502", conducted: 28, attended: 24, threshold: 75, trend: "stable" },
    { id: "cs503", name: "Operating Systems", code: "CS503", conducted: 26, attended: 17, threshold: 75, trend: "critical" },
  ],
  assessments: [
    { component: "Continuous Assessment 1 (CIA-1)", type: "Internal Test", maxMarks: 50, obtained: 34, status: "GRADED" },
    { component: "Module Quiz 1", type: "Quiz", maxMarks: 10, obtained: 0, status: "OFFICIAL_ZERO" },
    { component: "Theory Assignment 1", type: "Assignment", maxMarks: 20, obtained: 18, status: "GRADED" },
    { component: "OS Lab Practical 1", type: "Lab", maxMarks: 30, obtained: 22, status: "GRADED" },
    { component: "Continuous Assessment 2 (CIA-2)", type: "Internal Test", maxMarks: 50, obtained: null, status: "PENDING_EVAL" },
  ],
  tasks: [
    { id: "1", title: "Submit DBMS Assignment 2", source: "Faculty Task", deadline: "Tomorrow 23:59", priority: "critical", status: "pending" },
    { id: "2", title: "Review B-Tree & Normalization Module", source: "AI Recovery Plan", deadline: "Today 22:00", priority: "high", status: "pending" },
    { id: "3", title: "Comp Networks: Attend next 3 lectures", source: "AI Recovery Plan", deadline: "This week", priority: "critical", status: "pending" },
    { id: "4", title: "OS Process Sync Report", source: "Coursework", deadline: "Completed", priority: "medium", status: "completed" },
  ],
  interventionCases: [
    { id: "CAS-BCREC-2026-0042", status: "PENDING_APPROVAL", urgency: "URGENT", openedAt: "2026-10-07T09:30:00Z" },
  ],
};

export default function StudentDetailPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "attendance" | "assessments" | "tasks">("overview");
  const student = STUDENT_DATA;

  const tabs = [
    { id: "overview", label: "Overview & Subjects", icon: BookOpen },
    { id: "attendance", label: "Attendance Decay", icon: Clock },
    { id: "assessments", label: "Assessment Results", icon: FileCheck },
    { id: "tasks", label: "Intervention Tasks", icon: ListTodo },
  ];

  return (
    <WebLayout>
      <div className="space-y-6 page-enter max-w-5xl mx-auto">
        {/* Breadcrumb & Navigation */}
        <div className="flex items-center gap-2 text-xs text-[#9DA3AE]">
          <Link href="/students" className="hover:text-white transition-colors flex items-center gap-1.5 font-medium">
            <ArrowLeft className="w-4 h-4" />
            <span>Student Directory</span>
          </Link>
          <span>/</span>
          <span className="text-[#FFFFFF] font-mono font-semibold">{student.rollNo}</span>
        </div>

        {/* Header - Linear Style */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-5 pb-5 border-b border-white/[0.08]">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-md bg-[#16171A] border border-white/[0.12] flex items-center justify-center text-sm font-semibold text-[#FFFFFF] font-mono shadow-sm">
              AS
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold tracking-tight text-[#FFFFFF]">
                  {student.name}
                </h1>
                <span className="px-2.5 py-1 rounded-md text-xs font-mono font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-400 linear-pulse-dot" />
                  CRITICAL RISK
                </span>
              </div>
              <p className="text-sm text-[#9DA3AE]">
                {student.programme} · Batch {student.batch} · Semester {student.semester}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/queue"
              className="h-8 px-3 text-[13px] font-medium bg-[#FFFFFF] hover:bg-white/90 text-[#08090A] rounded-lg transition-all active:scale-[0.98] shadow-sm flex items-center"
            >
              Review Active Plan
            </Link>
          </div>
        </div>

        {/* 4 Key Stat Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
          <div className="p-4 rounded-xl bg-[#121316] border border-white/[0.08] space-y-1.5">
            <div className="text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">Aggregate Attendance</div>
            <div className="text-xl font-bold font-mono text-rose-400">
              {student.attendance}%
            </div>
            <div className="text-xs text-[#8A8F98]">Min 75% required</div>
          </div>

          <div className="p-4 rounded-xl bg-[#121316] border border-white/[0.08] space-y-1.5">
            <div className="text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">Academic Trend</div>
            <div className="text-xl font-bold font-mono text-amber-400">
              ↓ Declining
            </div>
            <div className="text-xs text-[#8A8F98]">CIA-1 avg decay -2.4%</div>
          </div>

          <div className="p-4 rounded-xl bg-[#121316] border border-white/[0.08] space-y-1.5">
            <div className="text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">Overdue Tasks</div>
            <div className="text-xl font-bold font-mono text-rose-400">
              {student.overdueTasks}
            </div>
            <div className="text-xs text-[#8A8F98]">Recovery tasks pending</div>
          </div>

          <div className="p-4 rounded-xl bg-[#121316] border border-white/[0.08] space-y-1.5">
            <div className="text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">Mentor Case</div>
            <div className="text-base font-semibold font-mono text-[#A5AEF6] mt-1">
              PENDING APPROVAL
            </div>
            <div className="text-xs text-[#8A8F98]">Assigned to {student.mentor}</div>
          </div>
        </div>

        {/* Tab Navigation with Linear-style sliding motion indicator */}
        <div className="flex items-center gap-1 border-b border-white/[0.08]">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`relative px-3.5 py-2.5 text-xs font-medium transition-colors flex items-center gap-2 ${
                  isActive
                    ? "text-[#FFFFFF]"
                    : "text-[#9DA3AE] hover:text-[#FFFFFF]"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-[#5E6AD2]" : "text-[#8A8F98]"}`} />
                <span>{tab.label}</span>
                {isActive && (
                  <motion.div
                    layoutId="linearTabActiveIndicator"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#5E6AD2]"
                    transition={{ type: "spring", stiffness: 500, damping: 35 }}
                  />
                )}
              </button>
            );
          })}
        </div>

        {/* Tab Content Panels */}
        <div className="space-y-6">
          {/* Course Attendance List */}
          <div className="rounded-xl border border-white/[0.08] bg-[#121316] overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b border-white/[0.08] flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-[#FFFFFF] font-mono">
                Course-wise Attendance & Recovery Math
              </h2>
              <span className="text-xs font-mono text-[#9DA3AE]">Deterministic Engine Projection</span>
            </div>

            <div className="divide-y divide-white/[0.06]">
              {student.courses.map((course) => {
                const pct = ((course.attended / course.conducted) * 100).toFixed(1);
                const isUnder = parseFloat(pct) < course.threshold;

                return (
                  <div key={course.id} className="p-3 hover:bg-white/[0.02] transition-colors flex items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2.5">
                        <span className="font-semibold text-base text-[#FFFFFF]">{course.name}</span>
                        <code className="text-xs font-mono text-[#9DA3AE] bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.06]">{course.code}</code>
                      </div>
                      <div className="text-sm text-[#9DA3AE]">
                        Attended <span className="text-white font-mono font-semibold">{course.attended}</span> of {course.conducted} lectures
                      </div>
                    </div>

                    <div className="flex items-center gap-5">
                      <div className="text-right">
                        <div className={`font-mono font-bold text-base ${isUnder ? "text-rose-400" : "text-emerald-400"}`}>
                          {pct}%
                        </div>
                        <div className="text-xs text-[#8A8F98] font-mono">Min {course.threshold}%</div>
                      </div>

                      <span
                        className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold ${
                          isUnder
                            ? "bg-rose-500/15 text-rose-400 border border-rose-500/25"
                            : "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
                        }`}
                      >
                        {isUnder ? "DETENTION RISK" : "COMPLIANT"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Assessment Components */}
          <div className="rounded-xl border border-white/[0.08] bg-[#121316] overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b border-white/[0.08] flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-[#FFFFFF] font-mono">
                Continuous Evaluation & Assessment Log
              </h2>
              <span className="text-xs font-mono text-[#9DA3AE]">Verified Institutional Data</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse" role="table">
                <thead>
                  <tr className="border-b border-white/[0.08] bg-white/[0.02]">
                    <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                      Component
                    </th>
                    <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                      Category
                    </th>
                    <th className="py-3 px-4 text-right text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                      Max Marks
                    </th>
                    <th className="py-3 px-4 text-right text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                      Score Obtained
                    </th>
                    <th className="py-3 px-4 text-right text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold pr-5">
                      Evaluation State
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {student.assessments.map((a) => (
                    <tr key={a.component} className="hover:bg-white/[0.03] transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-sm text-[#FFFFFF]">
                        {a.component}
                      </td>
                      <td className="py-2.5 px-3 text-sm text-[#9DA3AE]">
                        {a.type}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-sm text-[#ECEEF0]">
                        {a.maxMarks}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-sm font-bold">
                        {a.obtained !== null ? (
                          <span className={a.obtained === 0 ? "text-rose-400" : "text-[#FFFFFF]"}>
                            {a.obtained}
                          </span>
                        ) : (
                          <span className="text-[#6E7480]">—</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-xs pr-5">
                        <span
                          className={`px-2.5 py-1 rounded-md font-semibold ${
                            a.status === "GRADED"
                              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
                              : a.status === "OFFICIAL_ZERO"
                              ? "bg-rose-500/15 text-rose-400 border border-rose-500/25 font-bold"
                              : "bg-white/[0.04] text-[#9DA3AE] border border-white/[0.08]"
                          }`}
                        >
                          {a.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </WebLayout>
  );
}
