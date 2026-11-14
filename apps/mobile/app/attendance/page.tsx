"use client";

import React, { useState } from "react";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  CheckCircle2,
  XCircle,
  FileQuestion,
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

export default function DesktopAttendancePage() {
  const [selectedCourse, setSelectedCourse] = useState<CourseAttendance>(COURSES_DATA[0]);
  const [showDiscrepancyModal, setShowDiscrepancyModal] = useState(false);
  const [discrepancySubmitted, setDiscrepancySubmitted] = useState(false);

  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Institutional Attendance Ledger</h1>
            <p className="text-xs text-[#8A8F98] mt-0.5">
              Verified BCREC Attendance Ledger · Institutional Rule: <span className="font-mono text-white font-semibold">Min 75.0% without condonation penalty</span>
            </p>
          </div>
          <Button
            size="md"
            variant="secondary"
            onClick={() => setShowDiscrepancyModal(true)}
            icon={<FileQuestion className="w-3.5 h-3.5 text-[#5E6AD2]" />}
          >
            Report Discrepancy
          </Button>
        </div>

        {/* Aggregate Status Banner */}
        <Card className="p-4 border-rose-500/25 bg-gradient-to-r from-[#141014] to-[#0D0E10] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <StatusBadge variant="critical" showPulse>
                1 COURSE BELOW THRESHOLD
              </StatusBadge>
              <span className="text-xs font-semibold text-white">Cumulative Aggregate: 80.2% (89 / 111 lectures)</span>
            </div>
            <p className="text-xs text-[#8A8F98]">
              CS501 (DBMS) is at 73.3%. Attend the next 3 consecutive lectures to restore exam clearance before next week.
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right font-mono text-xs">
              <span className="text-[#8A8F98] block text-[10px]">Overall Margin</span>
              <span className="text-emerald-400 font-bold">+7 Safe Sessions</span>
            </div>
          </div>
        </Card>

        {/* 2-Column Desktop Ledger: Left Subjects Grid (7 Cols), Right Course Session History (5 Cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: All Courses Ledger (7 Cols) */}
          <div className="lg:col-span-7 space-y-3">
            <div className="flex items-center justify-between text-xs text-[#8A8F98] font-semibold uppercase tracking-wider">
              <span>Enrolled Courses</span>
              <span>Click a course to view session audit</span>
            </div>

            <div className="space-y-2.5">
              {COURSES_DATA.map((course) => {
                const pct = ((course.attended / course.conducted) * 100).toFixed(1);
                const isSelected = selectedCourse.id === course.id;

                return (
                  <Card
                    key={course.id}
                    onClick={() => setSelectedCourse(course)}
                    className={`p-4 cursor-pointer transition-all ${
                      isSelected
                        ? "border-[#5E6AD2] bg-[#121316] shadow-md shadow-indigo-500/10"
                        : "border-white/[0.08] hover:border-white/[0.15] bg-[#0D0E10]"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-sm font-semibold text-white truncate">{course.name}</span>
                          <span className="text-[10px] font-mono text-[#8A8F98] px-1.5 py-0.2 rounded bg-white/[0.04]">
                            {course.code}
                          </span>
                        </div>
                        <p className="text-xs text-[#8A8F98]">
                          {course.faculty} · <span className="font-mono text-white/80">{course.attended}/{course.conducted} classes</span>
                        </p>
                      </div>

                      <div className="text-right shrink-0">
                        <span
                          className={`text-base font-bold font-mono ${
                            course.status === "critical" ? "text-rose-400" : "text-emerald-400"
                          }`}
                        >
                          {pct}%
                        </span>
                        <span className="block text-[11px] text-[#8A8F98] font-mono">
                          {course.safeBunks === 0 ? "0 bunks left" : `${course.safeBunks} safe bunks`}
                        </span>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          course.status === "critical" ? "bg-rose-500" : "bg-emerald-500"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Right Column: Selected Course Session History (5 Cols) */}
          <div className="lg:col-span-5 space-y-3">
            <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3">
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
                <div>
                  <h3 className="text-sm font-semibold text-white">{selectedCourse.name}</h3>
                  <p className="text-xs text-[#8A8F98] font-mono">{selectedCourse.code} · Session Log</p>
                </div>
                <span
                  className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                    selectedCourse.status === "critical"
                      ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                      : "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                  }`}
                >
                  {((selectedCourse.attended / selectedCourse.conducted) * 100).toFixed(1)}%
                </span>
              </div>

              {/* Session list */}
              <div className="space-y-2">
                <span className="text-[11px] font-semibold text-[#8A8F98] uppercase tracking-wider block">
                  Recent Attendance Records:
                </span>

                <div className="space-y-1.5 max-h-[360px] overflow-y-auto pr-1">
                  {selectedCourse.recentSessions.map((session, sIdx) => (
                    <div
                      key={sIdx}
                      className="p-2.5 rounded bg-[#121316] border border-white/[0.04] flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        {session.status === "present" ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                        )}
                        <div>
                          <div className="font-medium text-white">{session.date}</div>
                          <div className="text-[11px] text-[#8A8F98]">{session.time}</div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {session.note && (
                          <span className="text-[10px] text-[#8A8F98] italic hidden sm:inline">
                            {session.note}
                          </span>
                        )}
                        <span
                          className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-semibold ${
                            session.status === "present"
                              ? "bg-emerald-500/15 text-emerald-300"
                              : "bg-rose-500/15 text-rose-300"
                          }`}
                        >
                          {session.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {selectedCourse.status === "critical" && (
                <div className="pt-3 border-t border-white/[0.06] space-y-2">
                  <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/25 text-xs text-rose-300 space-y-1">
                    <span className="font-semibold block">⚠️ Action Required</span>
                    <p className="text-[11px] text-rose-300/90 leading-relaxed">
                      You need to attend the next 3 consecutive lectures to reach 75.8% before the final exam list freezes.
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="danger"
                    className="w-full"
                    onClick={() => setShowDiscrepancyModal(true)}
                  >
                    Contest Biometric Absence
                  </Button>
                </div>
              )}
            </Card>
          </div>
        </div>

        {/* Discrepancy Modal */}
        {showDiscrepancyModal && (
          <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
            <Card className="max-w-md w-full p-5 space-y-3.5 bg-[#121316] border-white/[0.12]">
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
                    If a biometric reader timed out or you submitted medical leave documentation to your mentor, submit a correction request:
                  </p>
                  <div>
                    <label className="block text-[11px] text-[#8A8F98] mb-1">Subject</label>
                    <input
                      type="text"
                      disabled
                      value={`${selectedCourse.code} - ${selectedCourse.name}`}
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
                  <p className="text-sm font-semibold text-white">Discrepancy Routed to Faculty Drawer</p>
                  <p className="text-xs text-[#8A8F98]">
                    Record quarantined. Your class teacher has been notified to verify attendance logs against biometric timestamps.
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
    </StudentLayout>
  );
}
