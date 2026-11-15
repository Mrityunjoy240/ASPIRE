"use client";

import React, { useEffect, useState } from "react";
import { WebLayout } from "@/components/layout/WebLayout";
import { approveCase, fetchCaseQueue, type CaseQueueItem } from "@/lib/api";
import { X } from "lucide-react";

type UrgencyVariant = "critical" | "warning" | "monitor";

type QueueRow = CaseQueueItem & {
  attendance: number | null;
  source: "live" | "demo";
};

// Authored in canonical DM-SS03 order (03 §6.2): URGENT by exam ASC (NULL last),
// then ATTENTION by days-since-action DESC (NULL first), then MONITOR; never
// re-ranked in the client.
const DEMO_ROWS: QueueRow[] = [
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
    ATTENDANCE_RISK: "Attendance Danger",
    ASSESSMENT_TREND_DECLINING: "Grade Decay",
    EXAM_APPROACHING: "Exam Proximate",
  };
  return events.map((e) => eventMap[e] || e).join(", ");
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
        setRows(items.map((item) => ({ ...item, attendance: null, source: "live" as const })));
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
      setRows((prev) =>
        prev.map((r) =>
          r.case_id === row.case_id ? { ...r, status: "ACTIVE" } : r
        )
      );
      setNotice({
        kind: "success",
        text: `Plan approved for ${row.student_name} — case transitioned to ACTIVE.`,
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

  const criticalCount = rows.filter((r) => mapUrgency(r.urgency_band) === "critical").length;
  const warningCount = rows.filter((r) => mapUrgency(r.urgency_band) === "warning").length;

  return (
    <WebLayout>
      <div className="space-y-6 page-enter">
        {/* Header Toolbar — Clear & Polished */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-5 pb-5 border-b border-white/[0.08]">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold tracking-tight text-[#FFFFFF]">
                Triage Queue
              </h1>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-white/[0.06] text-[#ECEEF0] border border-white/[0.10]">
                DM-SS03 Canonical Order
              </span>
              <span
                className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${
                  isLive
                    ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
                    : "bg-white/[0.05] text-[#9DA3AE] border border-white/[0.08]"
                }`}
              >
                {isLive ? "LIVE REST API" : "DEMO FIXTURE"}
              </span>
            </div>
            <p className="text-[13px] text-[#9DA3AE]">
              Prioritized mentor workload: Urgency Band → Nearest Exam (ASC) → Days Inactive (DESC)
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-3 px-3 py-1.5 rounded-lg bg-[#121316] border border-white/[0.08] text-xs font-mono">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-400 linear-pulse-dot" />
                <span className="text-rose-400 font-bold text-sm">{criticalCount}</span>
                <span className="text-[#9DA3AE]">Critical</span>
              </div>
              <span className="text-[#6E7480]">|</span>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                <span className="text-amber-400 font-bold text-sm">{warningCount}</span>
                <span className="text-[#9DA3AE]">Attention</span>
              </div>
            </div>
          </div>
        </div>

        {/* Notice alert */}
        {notice && (
          <div
            role="status"
            className={`rounded-lg border px-4 py-3 text-xs font-medium flex items-center justify-between ${
              notice.kind === "success"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                : notice.kind === "error"
                ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                : "border-white/10 bg-white/[0.04] text-[#ECEEF0]"
            }`}
          >
            <span className="text-sm">{notice.text}</span>
            <button
              onClick={() => setNotice(null)}
              className="text-[#9DA3AE] hover:text-white ml-2 text-sm leading-none p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Linear High-Visibility Data Table */}
        <div className="rounded-xl border border-white/[0.08] bg-[#121316] overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse" role="table">
              <thead>
                <tr className="border-b border-white/[0.08] bg-white/[0.02]">
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Student
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Urgency
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Attendance
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Case Status
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Signals
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Exam Prox
                  </th>
                  <th className="py-2.5 px-3 text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold">
                    Staleness
                  </th>
                  <th className="py-3 px-4 text-right text-xs font-mono uppercase tracking-wider text-[#9DA3AE] font-semibold pr-5">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {rows.map((caseItem) => {
                  const isCritical = caseItem.urgency_band === "URGENT";
                  const canApprove = caseItem.status === "PENDING_APPROVAL";
                  const isApproving = pendingId === caseItem.case_id;

                  return (
                    <tr
                      key={caseItem.case_id}
                      className="hover:bg-white/[0.03] transition-colors group"
                    >
                      {/* Student info */}
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-sm text-[#FFFFFF] group-hover:text-white transition-colors">
                          {caseItem.student_name}
                        </div>
                        <div className="font-mono text-xs text-[#9DA3AE] mt-0.5">
                          {caseItem.student_roll}
                        </div>
                      </td>

                      {/* Urgency */}
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-semibold ${
                            isCritical
                              ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                              : caseItem.urgency_band === "ATTENTION"
                              ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                              : "bg-white/[0.05] text-[#ECEEF0] border border-white/[0.10]"
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isCritical ? "bg-rose-400" : "bg-amber-400"
                            }`}
                          />
                          {caseItem.urgency_band}
                        </span>
                      </td>

                      {/* Attendance */}
                      <td className="py-2.5 px-3">
                        {caseItem.attendance != null ? (
                          <div className="flex items-baseline gap-1.5">
                            <span
                              className={`font-mono font-bold text-sm ${
                                caseItem.attendance < 75
                                  ? "text-rose-400"
                                  : caseItem.attendance < 80
                                  ? "text-amber-400"
                                  : "text-emerald-400"
                              }`}
                            >
                              {caseItem.attendance}%
                            </span>
                            <span className="text-xs text-[#6E7480] font-mono">/ 75% min</span>
                          </div>
                        ) : (
                          <span className="text-[#6E7480] font-mono text-sm">—</span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex px-2.5 py-1 rounded-md text-xs font-mono font-semibold ${
                            caseItem.status === "PENDING_APPROVAL"
                              ? "bg-[#5E6AD2]/20 text-[#A5AEF6] border border-[#5E6AD2]/35"
                              : caseItem.status === "ACTIVE"
                              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                              : caseItem.status === "ESCALATION_REQUIRED"
                              ? "bg-rose-500/20 text-rose-400 border border-rose-500/35"
                              : "bg-white/[0.05] text-[#ECEEF0] border border-white/[0.08]"
                          }`}
                        >
                          {caseItem.status.replace(/_/g, " ")}
                        </span>
                      </td>

                      {/* Triggers */}
                      <td className="py-2.5 px-3">
                        <span className="text-xs text-[#ECEEF0] truncate max-w-[170px] block font-medium" title={caseItem.trigger_events.join(", ")}>
                          {getEventLabels(caseItem.trigger_events)}
                        </span>
                      </td>

                      {/* Nearest Exam */}
                      <td className="py-2.5 px-3 font-mono text-sm text-[#FFFFFF]">
                        {caseItem.nearest_exam_days != null ? (
                          <span className={caseItem.nearest_exam_days <= 7 ? "text-rose-400 font-bold" : "text-[#ECEEF0] font-semibold"}>
                            {caseItem.nearest_exam_days} days
                          </span>
                        ) : (
                          <span className="text-[#6E7480]">—</span>
                        )}
                      </td>

                      {/* Staleness */}
                      <td className="py-2.5 px-3">
                        <span
                          className={`font-mono text-xs px-2.5 py-0.5 rounded-md font-semibold ${
                            (caseItem.days_since_last_action ?? 0) > 3
                              ? "text-rose-400 bg-rose-500/15 border border-rose-500/30"
                              : "text-[#9DA3AE] bg-white/[0.04]"
                          }`}
                        >
                          {caseItem.days_since_last_action ?? 0}d ago
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="py-2.5 px-3 pr-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {canApprove && (
                            <button
                              disabled={isApproving}
                              onClick={() => handleApprove(caseItem)}
                              className="h-7 px-2.5 text-xs font-semibold rounded-md bg-[#5E6AD2] hover:bg-[#6875E3] text-white transition-all active:scale-[0.98] disabled:opacity-50 shadow-sm"
                            >
                              {isApproving ? "Approving…" : "Approve Plan"}
                            </button>
                          )}
                          <button
                            onClick={() => console.log("Trace", caseItem.case_id)}
                            className="h-7 px-2.5 text-xs font-medium rounded-md text-[#ECEEF0] hover:text-[#FFFFFF] bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] transition-colors"
                          >
                            Trace
                          </button>
                        </div>
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
