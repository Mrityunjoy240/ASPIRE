"use client";

import React from "react";
import { WebLayout } from "@/components/layout/WebLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";

const QUEUE_DATA = [
  {
    id: "CAS-BCREC-2026-0042",
    studentName: "Ananya Sharma",
    rollNo: "BCREC-CS-2026-042",
    urgency: "critical" as const,
    attendance: 73.3,
    status: "PENDING_APPROVAL",
    triggerEvents: ["ATTENDANCE_RISK", "ASSESSMENT_TREND_DECLINING"],
    openedAt: "2026-10-07T09:30:00Z",
    nearestExamDays: 8,
    daysSinceLastAction: 0,
  },
  {
    id: "CAS-BCREC-2026-0038",
    studentName: "Rohit Kumar",
    rollNo: "BCREC-CS-2026-018",
    urgency: "critical" as const,
    attendance: 68.5,
    status: "PLAN_PROPOSED",
    triggerEvents: ["ATTENDANCE_RISK"],
    openedAt: "2026-10-06T14:22:00Z",
    nearestExamDays: 12,
    daysSinceLastAction: 1,
  },
  {
    id: "CAS-BCREC-2026-0035",
    studentName: "Priya Singh",
    rollNo: "BCREC-CS-2026-029",
    urgency: "warning" as const,
    attendance: 78.2,
    status: "IN_REVIEW",
    triggerEvents: ["ASSESSMENT_TREND_DECLINING"],
    openedAt: "2026-10-05T11:15:00Z",
    nearestExamDays: 15,
    daysSinceLastAction: 2,
  },
  {
    id: "CAS-BCREC-2026-0031",
    studentName: "Vikram Patel",
    rollNo: "BCREC-EE-2026-007",
    urgency: "warning" as const,
    attendance: 76.8,
    status: "OPEN",
    triggerEvents: ["ATTENDANCE_RISK", "EXAM_APPROACHING"],
    openedAt: "2026-10-04T09:45:00Z",
    nearestExamDays: 5,
    daysSinceLastAction: 3,
  },
  {
    id: "CAS-BCREC-2026-0028",
    studentName: "Sneha Reddy",
    rollNo: "BCREC-CS-2026-011",
    urgency: "monitor" as const,
    attendance: 82.1,
    status: "MONITORING",
    triggerEvents: ["ASSESSMENT_TREND_DECLINING"],
    openedAt: "2026-10-03T16:20:00Z",
    nearestExamDays: 22,
    daysSinceLastAction: 4,
  },
  {
    id: "CAS-BCREC-2026-0025",
    studentName: "Arjun Mehta",
    rollNo: "BCREC-ME-2026-042",
    urgency: "critical" as const,
    attendance: 65.4,
    status: "ESCALATION_REQUIRED",
    triggerEvents: ["ATTENDANCE_RISK", "ASSESSMENT_TREND_DECLINING", "EXAM_APPROACHING"],
    openedAt: "2026-10-02T10:00:00Z",
    nearestExamDays: 3,
    daysSinceLastAction: 5,
  },
  {
    id: "CAS-BCREC-2026-0022",
    studentName: "Kavya Nair",
    rollNo: "BCREC-CS-2026-033",
    urgency: "warning" as const,
    attendance: 79.5,
    status: "ACTIVE",
    triggerEvents: ["ASSESSMENT_TREND_DECLINING"],
    openedAt: "2026-10-01T13:30:00Z",
    nearestExamDays: 18,
    daysSinceLastAction: 6,
  },
];

function getUrgencyVariant(urgency: string): "critical" | "warning" | "safe" {
  switch (urgency) {
    case "critical": return "critical";
    case "warning": return "warning";
    default: return "safe";
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

function getEventLabels(events: string[]) {
  const eventMap: Record<string, string> = {
    "ATTENDANCE_RISK": "Attendance Risk",
    "ASSESSMENT_TREND_DECLINING": "Assessment Declining",
    "EXAM_APPROACHING": "Exam Approaching",
  };
  return events.map(e => eventMap[e] || e).join(", ");
}

export default function QueuePage() {
  // Sort per DM-SS03: Urgency Band  Exam Proximity  Days Since Last Action
  const urgencyRank = { critical: 0, warning: 1, monitor: 2 };
  const sortedQueue = [...QUEUE_DATA].sort((a, b) => {
    const urgencyDiff = urgencyRank[a.urgency] - urgencyRank[b.urgency];
    if (urgencyDiff !== 0) return urgencyDiff;
    const examDiff = (a.nearestExamDays || 999) - (b.nearestExamDays || 999);
    if (examDiff !== 0) return examDiff;
    return (a.daysSinceLastAction || 999) - (b.daysSinceLastAction || 999);
  });

  const criticalCount = QUEUE_DATA.filter(c => c.urgency === "critical").length;
  const warningCount = QUEUE_DATA.filter(c => c.urgency === "warning").length;
  const resolvedCount = 12; // mock

  return (
    <WebLayout>
      <div className="space-y-6 animate-fade-in">
        {/* Header with Metrics */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 mb-6">
          <div>
            <h1 className="text-page-title">Triage Queue</h1>
            <p className="text-body text-slate-400 mt-1">Mentor priority triage · Sorted per DM-SS03</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <div className="glass-card px-4 py-3">
              <div className="text-2xl font-extrabold font-mono text-rose-400">{criticalCount}</div>
              <div className="text-micro text-slate-500">Critical</div>
            </div>
            <div className="glass-card px-4 py-3">
              <div className="text-2xl font-extrabold font-mono text-amber-400">{warningCount}</div>
              <div className="text-micro text-slate-500">Warning</div>
            </div>
            <div className="glass-card px-4 py-3">
              <div className="text-2xl font-extrabold font-mono text-emerald-400">{resolvedCount}</div>
              <div className="text-micro text-slate-500">Resolved</div>
            </div>
          </div>
        </div>

        {/* Queue Table */}
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full" role="table">
              <thead>
                <tr className="border-b border-white/[0.08]">
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Student</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Roll No</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Urgency</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Attendance</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Status</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Triggers</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Exam In</th>
                  <th className="px-4 py-3 text-left text-micro text-slate-500 uppercase tracking-wider font-semibold">Staleness</th>
                  <th className="px-4 py-3 text-right text-micro text-slate-500 uppercase tracking-wider font-semibold pr-4">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {sortedQueue.map((caseItem) => (
                  <tr key={caseItem.id} className="hover:bg-white/[0.02] transition-colors">
<td className="px-4 py-4">
                      <div>
                        <p className="font-semibold text-white">{caseItem.studentName}</p>
                        <p className="text-micro text-slate-500">Mentor: Dr. A. Sen</p>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <code className="font-mono text-slate-300">{caseItem.rollNo}</code>
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge variant={getUrgencyVariant(caseItem.urgency)} showPulse={caseItem.urgency === "critical"}>
                        {caseItem.urgency.toUpperCase()}
                      </StatusBadge>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-2">
                        <span className={`font-mono font-bold ${caseItem.attendance < 75 ? "text-rose-400" : caseItem.attendance < 80 ? "text-amber-400" : "text-emerald-400"}`}>
                          {caseItem.attendance}%
                        </span>
                        <span className="text-micro text-slate-500">/ 75%</span>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      {getStatusBadge(caseItem.status)}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-wrap gap-1">
                        {caseItem.triggerEvents.map((event, i) => (
                          <span key={i} className="px-2 py-0.5 bg-white/[0.05] rounded text-xs text-slate-400">
                            {getEventLabels([event])}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className="font-mono text-slate-300">
                        {caseItem.nearestExamDays} day{caseItem.nearestExamDays !== 1 ? "s" : ""}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono ${
                        caseItem.daysSinceLastAction > 3 ? "text-rose-400 bg-rose-500/10" :
                        caseItem.daysSinceLastAction > 1 ? "text-amber-400 bg-amber-500/10" :
                        "text-emerald-400 bg-emerald-500/10"
                      }`}>
                        <span className={caseItem.daysSinceLastAction > 3 ? "animate-pulse" : ""} aria-hidden="true"></span>
                        {caseItem.daysSinceLastAction}d
                      </span>
                    </td>
                    <td className="px-4 py-4 pr-4">
                      <div className="flex items-center gap-2 justify-end">
                        <Button size="sm" variant="ghost" onClick={() => console.log("Details", caseItem.id)}>
                          Details
                        </Button>
                        <Button size="sm" variant="primary" onClick={() => console.log("Approve", caseItem.id)}>
                          Approve
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => console.log("Escalate", caseItem.id)}>
                          Escalate
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
