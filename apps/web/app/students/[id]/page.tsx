"use client";

import React from "react";
import { WebLayout } from "@/components/layout/WebLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ProgressRing } from "@/components/ui/ProgressRing";

const STUDENT_DATA = {
  id: "STU-001",
  name: "Ananya Sharma",
  rollNo: "BCREC-CS-2026-042",
  batch: "2026-2030",
  programme: "B.Tech CSE (AIML)",
  semester: 5,
  email: "ananya.sharma@bcrec.ac.in",
  phone: "+91 98765 43210",
  mentor: "Dr. Ananya Sen",
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
    { component: "CIA-1", type: "CIA-1", maxMarks: 50, obtained: 34, status: "GRADED" },
    { component: "Quiz 1", type: "QUIZ", maxMarks: 10, obtained: 0, status: "OFFICIAL_ZERO" },
    { component: "Assignment 1", type: "ASSIGNMENT", maxMarks: 20, obtained: 18, status: "GRADED" },
    { component: "Lab 1", type: "LAB", maxMarks: 30, obtained: 22, status: "GRADED" },
    { component: "CIA-2", type: "CIA-2", maxMarks: 50, obtained: null, status: "SUBMITTED_PENDING_EVALUATION" },
    { component: "ESE", type: "ESE", maxMarks: 100, obtained: null, status: "NOT_SCHEDULED" },
  ],
  tasks: [
    { id: "1", title: "Submit Math Assignment 2", source: "Assessment", deadline: "Tomorrow 23:59", duration: "45 min", priority: "high", status: "pending" },
    { id: "2", title: "Review Module 3 Notes - Normalization", source: "AI Plan", deadline: "Today 22:00", duration: "60 min", priority: "high", status: "pending" },
    { id: "3", title: "DBMS Recovery: Attend next 3 classes", source: "AI Plan", deadline: "This week", duration: "3 sessions", priority: "critical", status: "pending" },
    { id: "4", title: "CN Lab Report - Week 2", source: "Calendar", deadline: "Friday 17:00", duration: "90 min", priority: "medium", status: "completed" },
  ],
  interventionCases: [
    { id: "CAS-BCREC-2026-0042", status: "PENDING_APPROVAL", urgency: "critical" as const, openedAt: "2026-10-07T09:30:00Z" },
  ],
};

function getRiskVariant(risk: string) {
  switch (risk) {
    case "critical": return "critical";
    case "warning": return "warning";
    default: return "safe";
  }
}

function getStatusColor(status: string) {
  switch (status) {
    case "GRADED": return "text-emerald-400";
    case "SUBMITTED_PENDING_EVALUATION": return "text-sky-400";
    case "OFFICIAL_ZERO": return "text-rose-400";
    case "WITHHELD": return "text-amber-400";
    case "CANCELLED": return "text-slate-400";
    case "NOT_SCHEDULED": return "text-slate-400";
    default: return "text-slate-400";
  }
}

function getStatusBadge(status: string) {
  const statusMap: Record<string, { label: string; variant: "critical" | "warning" | "safe" | "pending" | "overdue" | "pending-approval" }> = {
    "PENDING_APPROVAL": { label: "PENDING APPROVAL", variant: "pending-approval" },
    "PLAN_PROPOSED": { label: "PLAN PROPOSED", variant: "pending" },
    "IN_REVIEW": { label: "IN REVIEW", variant: "pending" },
    "OPEN": { label: "OPEN", variant: "warning" },
    "MONITORING": { label: "MONITORING", variant: "safe" },
    "ACTIVE": { label: "ACTIVE", variant: "safe" },
    "ESCALATION_REQUIRED": { label: "ESCALATION", variant: "critical" },
  };
  const s = statusMap[status] || { label: status, variant: "warning" };
  return <StatusBadge variant={s.variant}>{s.label}</StatusBadge>;
}

export default function StudentDetailPage() {
  const student = STUDENT_DATA;

  return (
    <WebLayout>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <header className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 mb-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center">
              <span className="text-2xl font-bold text-white">AS</span>
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-page-title">{student.name}</h1>
                <StatusBadge variant={getRiskVariant(student.attendanceRisk)} showPulse={student.attendanceRisk === "critical"}>
                  {student.attendanceRisk.toUpperCase()} RISK
                </StatusBadge>
              </div>
              <p className="text-body text-slate-400">{student.rollNo} · {student.programme} · Semester {student.semester}</p>
            </div>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => console.log("Message Mentor")}>
              Message Mentor
            </Button>
            <Button variant="primary" onClick={() => console.log("Create Plan")}>
              Create Plan
            </Button>
          </div>
        </header>

        {/* Key Metrics Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-micro text-slate-500">Attendance</p>
                <p className="text-3xl font-extrabold font-mono text-rose-400">{student.attendance}%</p>
              </div>
              <ProgressRing progress={student.attendance} size={60} strokeWidth={6} variant="critical" showLabel />
            </div>
          </Card>
          <Card>
            <p className="text-micro text-slate-500 mb-2">Assessment Trend</p>
            <div className="flex items-center gap-4">
              <p className="text-3xl font-extrabold font-mono text-amber-400">{student.assessmentTrend.charAt(0).toUpperCase() + student.assessmentTrend.slice(1)}</p>
              <span className="text-micro text-slate-500">-2.1% last week</span>
            </div>
          </Card>
          <Card>
            <p className="text-micro text-slate-500 mb-2">Overdue Tasks</p>
            <div className="flex items-center gap-4">
              <p className="text-3xl font-extrabold font-mono text-rose-400">{student.overdueTasks}</p>
              <StatusBadge variant="warning" showPulse={false}>Overdue</StatusBadge>
            </div>
          </Card>
          <Card>
            <p className="text-micro text-slate-500 mb-2">Active Cases</p>
            <div className="flex items-center gap-4">
              <p className="text-3xl font-extrabold font-mono text-rose-400">1</p>
              <StatusBadge variant="pending-approval">PENDING APPROVAL</StatusBadge>
            </div>
          </Card>
        </div>

          {/* Tabs Navigation */}
          <div className="flex gap-2 border-b border-white/[0.08] mb-6">
            {["Overview", "Attendance", "Assessments", "Tasks", "Interventions"].map((tab) => (
              <button key={tab} className="px-4 py-3 text-sm font-medium text-slate-400 hover:text-white border-b-2 border-transparent hover:border-indigo-500 transition-colors">
                {tab}
              </button>
            ))}
          </div>

          {/* Content Sections */}
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Left Column - Attendance & Assessments */}
            <div className="lg:col-span-2 space-y-6">
              {/* Attendance Section */}
              <Card>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-section-heading">Course Attendance</h3>
                  <Button size="sm" variant="ghost">View All</Button>
                </div>
                <div className="space-y-3">
                  {student.courses.map((course) => {
                    const pct = (course.attended / course.conducted) * 100;
                    const variant: "safe" | "warning" | "critical" = pct >= course.threshold ? "safe" : pct >= course.threshold - 5 ? "warning" : "critical";
                    return (
                      <div key={course.id} className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3 mb-2">
                              <h4 className="font-semibold text-white truncate">{course.name}</h4>
                              <span className="text-micro text-slate-500">{course.code}</span>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-slate-400">
                              <span>{course.attended}/{course.conducted} classes</span>
                              <StatusBadge variant={variant} showPulse={variant === "critical"}>
                                {pct.toFixed(1)}%
                              </StatusBadge>
                            </div>
                          </div>
                          <ProgressRing progress={pct} size={60} strokeWidth={6} variant={variant} showLabel />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Card>

              {/* Assessments Section */}
              <Card>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-section-heading">Assessment Components</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-white/[0.08]">
                        <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Component</th>
                        <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Type</th>
                        <th className="px-4 py-3 text-right text-micro text-slate-500 uppercase tracking-wider font-semibold">Max Marks</th>
                        <th className="px-4 py-3 text-right text-micro text-slate-500 uppercase tracking-wider font-semibold">Obtained</th>
                        <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {student.assessments.map((a) => (
                        <tr key={a.component}>
                          <td className="px-4 py-3">
                            <p className="font-medium text-white">{a.component}</p>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-micro text-slate-400">{a.type}</span>
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-white">{a.maxMarks}</td>
                          <td className="px-4 py-3 text-right font-mono">
                            {a.obtained !== null ? <span className="text-white">{a.obtained}</span> : <span className="text-slate-400"></span>}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold font-mono border ${getStatusColor(a.status)}`}>
                              {a.status.replace("_", " ")}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>

            {/* Right Column - Tasks & Interventions */}
            <div className="space-y-6">
              {/* Tasks */}
              <Card>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-section-heading">Active Tasks</h3>
                  <Button size="sm" variant="ghost">View All</Button>
                </div>
                <div className="space-y-3">
                  {student.tasks.map((task) => (
                    <div key={task.id} className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-semibold text-white truncate">{task.title}</h4>
                            <StatusBadge variant={task.priority === "critical" ? "critical" : task.priority === "high" ? "warning" : "safe"} showPulse={task.priority === "critical"}>
                              {task.priority}
                            </StatusBadge>
                          </div>
                          <p className="text-body text-slate-400 text-sm mb-2">{task.source}</p>
                          <div className="flex items-center gap-4 text-xs text-slate-400">
                            <span className="flex items-center gap-1">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-slate-500">
                                <circle cx="12" cy="12" r="10" />
                                <polyline points="12 6 12 12 16 14" />
                              </svg>
                              {task.deadline}
                            </span>
                            <span className="flex items-center gap-1">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-slate-500">
                                <circle cx="12" cy="12" r="10" />
                                <path d="M12 6v6l4 2" />
                              </svg>
                              {task.duration}
                            </span>
                          </div>
                        </div>
                        <StatusBadge variant={task.status === "completed" ? "safe" : task.status === "snoozed" ? "warning" : "pending"} showPulse={false}>
                          {task.status.charAt(0).toUpperCase() + task.status.slice(1)}
                        </StatusBadge>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Intervention Cases */}
              <Card>
                <h3 className="text-section-heading mb-4">Intervention Cases</h3>
                <div className="space-y-3">
                  {student.interventionCases.map((caseItem) => (
                    <div key={caseItem.id} className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h4 className="font-semibold text-white">Case #{caseItem.id}</h4>
                            <StatusBadge variant={caseItem.urgency} showPulse={caseItem.urgency === "critical"}>
                              {caseItem.urgency.toUpperCase()}
                            </StatusBadge>
                            {getStatusBadge(caseItem.status)}
                          </div>
                          <p className="text-micro text-slate-500">Opened {new Date(caseItem.openedAt).toLocaleDateString()}</p>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="primary">Review</Button>
                          <Button size="sm" variant="ghost">Details</Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
      </div>
    </WebLayout>
  );
}
