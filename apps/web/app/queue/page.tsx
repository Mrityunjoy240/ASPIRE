"use client";

import React, { useEffect, useState } from "react";
import { WebLayout } from "@/components/layout/WebLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { approveCase, fetchCaseQueue, type CaseQueueItem } from "@/lib/api";

type UrgencyVariant = "critical" | "warning" | "monitor";

type QueueRow = CaseQueueItem & {
  attendance: number | null;
  source: "live" | "demo";
};

const DEMO_ROWS: QueueRow[] = [
  {
    case_id: "CAS-BCREC-2026-0042",
    student_id: "00000000-0000-0000-0000-000000000042",
    student_name: "Ananya Sharma",
    student_roll: "BCREC-CS-2026-042",
    urgency_band: "URGENT",
    attendance: 73.3,
    status: "PENDING_APPROVAL",
    trigger_events: ["ATTENDANCE_RISK", "ASSESSMENT_TREND_DECLINING"],
    opened_at: "2026-10-07T09:30:00Z",
    nearest_exam_days: 8,
    days_since_last_action: 0,
    source: "demo",
  },
  {
    case_id: "CAS-BCREC-2026-0038",
    student_id: "00000000-0000-0000-0000-000000000038",
    student_name: "Rohit Kumar",
    student_roll: "BCREC-CS-2026-018",
    urgency_band: "URGENT",
    attendance: 68.5,
    status: "PLAN_PROPOSED",
    trigger_events: ["ATTENDANCE_RISK"],
    opened_at: "2026-10-06T14:22:00Z",
    nearest_exam_days: 12,
    days_since_last_action: 1,
    source: "demo",
  },
  {
    case_id: "CAS-BCREC-2026-0035",
    student_id: "00000000-0000-0000-0000-000000000035",
    student_name: "Priya Singh",
    student_roll: "BCREC-CS-2026-029",
    urgency_band: "ATTENTION",
    attendance: 78.2,
    status: "IN_REVIEW",
    trigger_events: ["ASSESSMENT_TREND_DECLINING"],
    opened_at: "2026-10-05T11:15:00Z",
    nearest_exam_days: 15,
    days_since_last_action: 2,
    source: "demo",
  },
  {
    case_id: "CAS-BCREC-2026-0031",
    student_id: "00000000-0000-0000-0000-000000000031",
    student_name: "Vikram Patel",
    student_roll: "BCREC-EE-2026-007",
    urgency_band: "ATTENTION",
    attendance: 76.8,
    status: "OPEN",
    trigger_events: ["ATTENDANCE_RISK", "EXAM_APPROACHING"],
    opened_at: "2026-10-04T09:45:00Z",
    nearest_exam_days: 5,
    days_since_last_action: 3,
    source: "demo",
  },
  {
    case_id: "CAS-BCREC-2026-0028",
    student_id: "00000000-0000-0000-0000-000000000028",
    student_name: "Sneha Reddy",
    student_roll: "BCREC-CS-2026-011",
    urgency_band: "MONITOR",
    attendance: 82.1,
    status: "MONITORING",
    trigger_events: ["ASSESSMENT_TREND_DECLINING"],
    opened_at: "2026-10-03T16:20:00Z",
    nearest_exam_days: 22,
    days_since_last_action: 4,
    source: "demo",
  },
  {
    case_id: "CAS-BCREC-2026-0025",
    student_id: "00000000-0000-0000-0000-000000000025",
    student_name: "Arjun Mehta",
    student_roll: "BCREC-ME-2026-042",
    urgency_band: "URGENT",
    attendance: 65.4,
    status: "ESCALATION_REQUIRED",
    trigger_events: ["ATTENDANCE_RISK", "ASSESSMENT_TREND_DECLINING", "EXAM_APPROACHING"],
    opened_at: "2026-10-02T10:00:00Z",
    nearest_exam_days: 3,
    days_since_last_action: 5,
    source: "demo",
  },
  {
    case_id: "CAS-BCREC-2026-0022",
    student_id: "00000000-0000-0000-0000-000000000022",
    student_name: "Kavya Nair",
    student_roll: "BCREC-CS-2026-033",
    urgency_band: "ATTENTION",
    attendance: 79.5,
    status: "ACTIVE",
    trigger_events: ["ASSESSMENT_TREND_DECLINING"],
    opened_at: "2026-10-01T13:30:00Z",
    nearest_exam_days: 18,
    days_since_last_action: 6,
    source: "demo",
  },
];

function mapUrgency(band: string): UrgencyVariant {
  switch (band) {
    case "URGENT": return "critical";
    case "ATTENTION": return "warning";
    default: return "monitor";
  }
}

function getEventLabels(events: string[]) {
  const eventMap: Record<string, string> = {
    "ATTENDANCE_RISK": "Attendance Risk",
    "ASSESSMENT_TREND_DECLINING": "Assessment Declining",
    "EXAM_APPROACHING": "Exam Approaching",
  };
  return events.map(e => eventMap[e] || e).join(", ");
}

interface Notice {
  kind: "success" | "error" | "info";
  text: string;
}

export default function QueuePage() {
  const [rows, setRows] = useState<QueueRow[]>(DEMO_ROWS);
  const [isLive, setIsLive] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const items = await fetchCaseQueue();
        if (cancelled) return;
        setRows(items.map(item => ({ ...item, attendance: null, source: "live" as const })));
        setIsLive(true);
        setNotice(null);
      } catch (err) {
        if (cancelled) return;
        setNotice({
          kind: "info",
          text: `Live queue unavailable — showing demo rows. ${err instanceof Error ? err.message : ""}`.trim(),
        });
      }
    })();
    return () => { cancelled = true; };
  }, []);

  async function handleApprove(row: QueueRow) {
    setPendingId(row.case_id);
    setNotice(null);
    try {
      await approveCase(row.case_id, "APPROVED");
      setRows(prev => prev.map(r =>
        r.case_id === row.case_id ? { ...r, status: "ACTIVE" } : r
      ));
      setNotice({
        kind: "success",
        text: `Plan approved for ${row.student_name} — case is now ACTIVE.`,
      });
    } catch (err) {
      setNotice({
        kind: "error",
        text: err instanceof Error ? err.message : "Approval failed",
      });
    } finally {
      setPendingId(null);
    }
  }

  // Sort per DM-SS03: Urgency Band → Exam Proximity → Days Since Last Action
  const urgencyRank: Record<UrgencyVariant, number> = { critical: 0, warning: 1, monitor: 2 };
  const sortedQueue = [...rows].sort((a, b) => {
    const urgencyDiff = urgencyRank[mapUrgency(a.urgency_band)] - urgencyRank[mapUrgency(b.urgency_band)];
    if (urgencyDiff !== 0) return urgencyDiff;
    const examDiff = (a.nearest_exam_days ?? 999) - (b.nearest_exam_days ?? 999);
    if (examDiff !== 0) return examDiff;
    return (a.days_since_last_action ?? 999) - (b.days_since_last_action ?? 999);
  });

  const criticalCount = rows.filter(r => mapUrgency(r.urgency_band) === "critical").length;
  const warningCount = rows.filter(r => mapUrgency(r.urgency_band) === "warning").length;
  const resolvedCount = 12; // mock

  const noticeClasses: Record<Notice["kind"], string> = {
    success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    error: "border-rose-500/30 bg-rose-500/10 text-rose-300",
    info: "border-white/10 bg-white/[0.04] text-slate-400",
  };

  return (
    <WebLayout>
      <div className="space-y-6 animate-fade-in">
        {/* Header with Metrics */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 mb-6">
          <div>
            <h1 className="text-page-title">Triage Queue</h1>
            <p className="text-body text-slate-400 mt-1">
              Mentor priority triage · Sorted per DM-SS03
              <span className="ml-2 font-mono text-xs">{isLive ? "· live" : "· demo"}</span>
            </p>
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

        {notice && (
          <div role="status" className={`rounded-lg border px-4 py-3 text-sm ${noticeClasses[notice.kind]}`}>
            {notice.text}
          </div>
        )}

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
                {sortedQueue.map((caseItem) => {
                  const urgency = mapUrgency(caseItem.urgency_band);
                  const canApprove = caseItem.status === "PENDING_APPROVAL";
                  const isApproving = pendingId === caseItem.case_id;
                  return (
                    <tr key={caseItem.case_id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-4 py-4">
                        <div>
                          <p className="font-semibold text-white">{caseItem.student_name}</p>
                          <p className="text-micro text-slate-500">Mentor: Dr. A. Sen</p>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <code className="font-mono text-slate-300">{caseItem.student_roll}</code>
                      </td>
                      <td className="px-4 py-4">
                        <StatusBadge
                          variant={urgency === "critical" ? "critical" : urgency === "warning" ? "warning" : "safe"}
                          showPulse={urgency === "critical"}
                        >
                          {caseItem.urgency_band.toUpperCase()}
                        </StatusBadge>
                      </td>
                      <td className="px-4 py-4">
                        {caseItem.attendance != null ? (
                          <div className="flex items-center gap-2">
                            <span className={`font-mono font-bold ${caseItem.attendance < 75 ? "text-rose-400" : caseItem.attendance < 80 ? "text-amber-400" : "text-emerald-400"}`}>
                              {caseItem.attendance}%
                            </span>
                            <span className="text-micro text-slate-500">/ 75%</span>
                          </div>
                        ) : (
                          <span className="font-mono text-slate-500" title="Attendance not in queue contract">—</span>
                        )}
                      </td>
                      <td className="px-4 py-4">
                        <StatusBadge variant={getStatusVariant(caseItem.status)}>{getStatusLabel(caseItem.status)}</StatusBadge>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex flex-wrap gap-1">
                          {caseItem.trigger_events.map((event, i) => (
                            <span key={i} className="px-2 py-0.5 bg-white/[0.05] rounded text-xs text-slate-400">
                              {getEventLabels([event])}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className="font-mono text-slate-300">
                          {caseItem.nearest_exam_days != null
                            ? `${caseItem.nearest_exam_days} day${caseItem.nearest_exam_days !== 1 ? "s" : ""}`
                            : "—"}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono ${
                          (caseItem.days_since_last_action ?? 0) > 3 ? "text-rose-400 bg-rose-500/10" :
                          (caseItem.days_since_last_action ?? 0) > 1 ? "text-amber-400 bg-amber-500/10" :
                          "text-emerald-400 bg-emerald-500/10"
                        }`}>
                          <span className={(caseItem.days_since_last_action ?? 0) > 3 ? "animate-pulse" : ""} aria-hidden="true"></span>
                          {caseItem.days_since_last_action ?? 0}d
                        </span>
                      </td>
                      <td className="px-4 py-4 pr-4">
                        <div className="flex items-center gap-2 justify-end">
                          <Button size="sm" variant="ghost" onClick={() => console.log("Details", caseItem.case_id)}>
                            Details
                          </Button>
                          {canApprove && (
                            <Button
                              size="sm"
                              variant="primary"
                              disabled={isApproving}
                              onClick={() => handleApprove(caseItem)}
                            >
                              {isApproving ? "Approving…" : "Approve"}
                            </Button>
                          )}
                          <Button size="sm" variant="danger" onClick={() => console.log("Escalate", caseItem.case_id)}>
                            Escalate
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </WebLayout>
  );
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    PENDING_APPROVAL: "PENDING APPROVAL",
    PLAN_PROPOSED: "PLAN PROPOSED",
    IN_REVIEW: "IN REVIEW",
    OPEN: "OPEN",
    MONITORING: "MONITORING",
    ACTIVE: "ACTIVE",
    ESCALATION_REQUIRED: "ESCALATION",
    REPLAN_REQUIRED: "REPLAN",
  };
  return labels[status] ?? status;
}

function getStatusVariant(status: string): "critical" | "warning" | "safe" | "pending" | "overdue" | "pending-approval" {
  const variants: Record<string, "critical" | "warning" | "safe" | "pending" | "overdue" | "pending-approval"> = {
    PENDING_APPROVAL: "pending-approval",
    PLAN_PROPOSED: "pending",
    IN_REVIEW: "pending",
    OPEN: "warning",
    MONITORING: "safe",
    ACTIVE: "safe",
    ESCALATION_REQUIRED: "critical",
    REPLAN_REQUIRED: "critical",
  };
  return variants[status] ?? "warning";
}
