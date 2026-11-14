"use client";

import React, { useState } from "react";
import { MobileLayout } from "@/components/MobileLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  CheckCircle2,
  XCircle,
  FileQuestion,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface CourseAttendance {
  id: string;
  name: string;
  code: string;
  faculty: string;
  attended: number;
  conducted: number;
  threshold: number;
  safeBunks: number;
  status: "critical" | "warning" | "safe";
  recentSessions: { date: string; time: string; status: "present" | "absent" | "excused"; note?: string }[];
}

const COURSES_DATA: CourseAttendance[] = [
  {
    id: "cs501",
    name: "Database Management Systems",
    code: "CS501",
    faculty: "Prof. Raj Kumar Samanta",
    attended: 22,
    conducted: 30,
    threshold: 75.0,
    safeBunks: 0,
    status: "critical",
    recentSessions: [
      { date: "14 Nov (Today)", time: "10:00 AM", status: "present", note: "Unit 3 Lecture" },
      { date: "12 Nov", time: "10:00 AM", status: "absent", note: "Fever / Medical slip pending" },
      { date: "10 Nov", time: "10:00 AM", status: "present", note: "Unit 2 Revision" },
      { date: "07 Nov", time: "10:00 AM", status: "absent", note: "Biometric timeout" },
      { date: "05 Nov", time: "10:00 AM", status: "present", note: "Normalization intro" },
    ],
  },
  {
    id: "cs502",
    name: "Operating Systems",
    code: "CS502",
    faculty: "Dr. Anirban Bose",
    attended: 23,
    conducted: 28,
    threshold: 75.0,
    safeBunks: 2,
    status: "safe",
    recentSessions: [
      { date: "13 Nov", time: "11:30 AM", status: "present" },
      { date: "11 Nov", time: "11:30 AM", status: "present" },
      { date: "08 Nov", time: "11:30 AM", status: "present" },
    ],
  },
  {
    id: "cs503",
    name: "Computer Networks",
    code: "CS503",
    faculty: "Prof. Suman Dasgupta",
    attended: 22,
    conducted: 28,
    threshold: 75.0,
    safeBunks: 1,
    status: "safe",
    recentSessions: [
      { date: "14 Nov", time: "01:00 PM", status: "present" },
      { date: "12 Nov", time: "01:00 PM", status: "present" },
      { date: "09 Nov", time: "01:00 PM", status: "absent" },
    ],
  },
  {
    id: "cs504",
    name: "AI & Machine Learning",
    code: "CS504",
    faculty: "Dr. Gour Sundar Mitra Thakur",
    attended: 22,
    conducted: 25,
    threshold: 75.0,
    safeBunks: 4,
    status: "safe",
    recentSessions: [
      { date: "13 Nov", time: "02:00 PM", status: "present" },
      { date: "10 Nov", time: "02:00 PM", status: "present" },
      { date: "06 Nov", time: "02:00 PM", status: "present" },
    ],
  },
];

export default function AttendanceLedgerPage() {
  const [expandedCourse, setExpandedCourse] = useState<string>("cs501");
  const [showDiscrepancyModal, setShowDiscrepancyModal] = useState(false);
  const [discrepancySubmitted, setDiscrepancySubmitted] = useState(false);

  return (
    <MobileLayout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white tracking-tight">Attendance Ledger</h1>
            <p className="text-xs text-[#8A8F98]">
              Verified Institutional Records · Minimum Threshold: <span className="text-white font-mono">75.0%</span>
            </p>
          </div>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setShowDiscrepancyModal(true)}
            icon={<FileQuestion className="w-3.5 h-3.5 text-[#5E6AD2]" />}
          >
            Report Discrepancy
          </Button>
        </div>

        {/* Aggregate Health Banner */}
        <Card className="p-3.5 border-rose-500/25 bg-gradient-to-r from-[#141014] to-[#0D0E10] flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <StatusBadge variant="critical" showPulse>
                1 SUBJECT BELOW THRESHOLD
              </StatusBadge>
              <span className="text-xs text-white font-semibold">Semester Aggregate: 80.2%</span>
            </div>
            <p className="text-[11px] text-[#8A8F98]">
              CS501 (DBMS) needs immediate attendance recovery to avoid ESE debarment.
            </p>
          </div>
          <div className="text-right shrink-0 font-mono">
            <span className="text-[10px] text-[#8A8F98] block">Overall Attended</span>
            <span className="text-sm font-bold text-white">89 / 111</span>
          </div>
        </Card>

        {/* Courses Ledger List */}
        <div className="space-y-2.5">
          {COURSES_DATA.map((course) => {
            const pct = ((course.attended / course.conducted) * 100).toFixed(1);
            const isExpanded = expandedCourse === course.id;

            return (
              <Card key={course.id} className="overflow-hidden border-white/[0.08]">
                {/* Clickable Course Header Row */}
                <div
                  onClick={() => setExpandedCourse(isExpanded ? "" : course.id)}
                  className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-white/[0.02] transition-colors"
                >
                  <div className="min-w-0 pr-2">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-xs font-semibold text-white truncate">{course.name}</span>
                      <span className="text-[10px] font-mono text-[#8A8F98] px-1 py-0.2 rounded bg-white/[0.04]">
                        {course.code}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#8A8F98]">
                      {course.faculty} · <span className="font-mono">{course.attended}/{course.conducted} classes</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right">
                      <span
                        className={`text-sm font-bold font-mono ${
                          course.status === "critical" ? "text-rose-400" : "text-emerald-400"
                        }`}
                      >
                        {pct}%
                      </span>
                      <span className="block text-[10px] text-[#8A8F98] font-mono">
                        {course.safeBunks === 0 ? "0 Bunks Left" : `${course.safeBunks} safe bunks`}
                      </span>
                    </div>

                    <div className="text-[#8A8F98]">
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </div>
                  </div>
                </div>

                {/* Expanded Session Timeline */}
                {isExpanded && (
                  <div className="px-3.5 pb-3.5 pt-1 border-t border-white/[0.06] bg-[#121316]/50 space-y-2">
                    <div className="flex items-center justify-between text-[11px] text-[#8A8F98]">
                      <span>Recent Session History:</span>
                      <span className="font-mono text-[10px]">Verified against Biometric & Faculty Grid</span>
                    </div>

                    <div className="space-y-1.5">
                      {course.recentSessions.map((session, sIdx) => (
                        <div
                          key={sIdx}
                          className="flex items-center justify-between p-2 rounded bg-[#0D0E10] border border-white/[0.04] text-xs"
                        >
                          <div className="flex items-center gap-2">
                            {session.status === "present" ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            ) : (
                              <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                            )}
                            <div>
                              <span className="text-white font-medium">{session.date}</span>
                              <span className="text-[#8A8F98] text-[10px] ml-2">({session.time})</span>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {session.note && (
                              <span className="text-[10px] text-[#8A8F98] italic hidden sm:inline">
                                {session.note}
                              </span>
                            )}
                            <span
                              className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                                session.status === "present"
                                  ? "bg-emerald-500/10 text-emerald-300"
                                  : "bg-rose-500/10 text-rose-300"
                              }`}
                            >
                              {session.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>

                    {course.status === "critical" && (
                      <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/25 flex items-center justify-between text-xs mt-2">
                        <span className="text-rose-300 text-[11px]">
                          ⚠️ Recovery Target: Attend next 3 classes without absence.
                        </span>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => setShowDiscrepancyModal(true)}
                        >
                          Contest Absences
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>

        {/* Discrepancy Modal */}
        {showDiscrepancyModal && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
            <Card className="max-w-md w-full p-4 space-y-3 bg-[#121316] border-white/[0.12]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileQuestion className="w-4 h-4 text-[#5E6AD2]" />
                  <h3 className="text-sm font-semibold text-white">Report Attendance Discrepancy</h3>
                </div>
                <button
                  onClick={() => {
                    setShowDiscrepancyModal(false);
                    setDiscrepancySubmitted(false);
                  }}
                  className="text-[#8A8F98] hover:text-white"
                >
                  ✕
                </button>
              </div>

              {!discrepancySubmitted ? (
                <div className="space-y-3 text-xs">
                  <p className="text-[#9DA3AE]">
                    If biometric reader timed out or you submitted a medical certificate to the HOD, request verification:
                  </p>
                  <div>
                    <label className="block text-[11px] text-[#8A8F98] mb-1">Subject</label>
                    <input
                      type="text"
                      disabled
                      value="CS501 - Database Management Systems"
                      className="w-full bg-[#0D0E10] border border-white/[0.08] p-2 rounded text-white font-mono text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-[#8A8F98] mb-1">Session Date</label>
                    <input
                      type="text"
                      defaultValue="12 Nov 2026 (10:00 AM)"
                      className="w-full bg-[#0D0E10] border border-white/[0.08] p-2 rounded text-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-[#8A8F98] mb-1">Reason / Provenance Proof</label>
                    <textarea
                      rows={3}
                      placeholder="e.g. Attended lecture in Room 302, biometric scanner showed network error. Medical slip submitted to mentor Prof. Samanta."
                      className="w-full bg-[#0D0E10] border border-white/[0.08] p-2 rounded text-white text-xs outline-none focus:border-[#5E6AD2]"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowDiscrepancyModal(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setDiscrepancySubmitted(true)}
                    >
                      Submit for Faculty Review
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-4 space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                  <p className="text-xs font-semibold text-white">Discrepancy Routed to Faculty Drawer</p>
                  <p className="text-[11px] text-[#8A8F98]">
                    Record quarantined. Your class teacher has been notified to verify attendance logs.
                  </p>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="mt-3"
                    onClick={() => {
                      setShowDiscrepancyModal(false);
                      setDiscrepancySubmitted(false);
                    }}
                  >
                    Done
                  </Button>
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    </MobileLayout>
  );
}
