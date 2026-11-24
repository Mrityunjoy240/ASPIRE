"use client";

import React from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Sparkles,
  ArrowRight,
  Clock,
  FileText,
  AlertCircle,
} from "lucide-react";

import { CLASSROOM_COURSES } from "./classroom-data";

export default function ClassroomDirectoryPage() {
  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-white tracking-tight">Subject Classrooms</h1>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-semibold">
                Google Classroom Style · 4 Enrolled
              </span>
            </div>
            <p className="text-xs text-[#8A8F98] mt-0.5">
              BCREC CSE Semester 5 · Access subject streams, notes, assignment submissions, or launch your NotebookLM Study Studio.
            </p>
          </div>

          <Link href="/study">
            <Button size="md" variant="secondary" icon={<Sparkles className="w-3.5 h-3.5 text-[#5E6AD2]" />}>
              Open Global Study Vault
            </Button>
          </Link>
        </div>

        {/* Classroom Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {CLASSROOM_COURSES.map((course) => (
            <Card
              key={course.id}
              className={`overflow-hidden bg-[#0D0E10] border ${course.accentBorder} hover:border-white/[0.25] transition-all flex flex-col justify-between group shadow-lg`}
            >
              {/* Card Top Banner (Google Classroom Header Style) */}
              <div
                className={`p-5 bg-gradient-to-r ${course.color} border-b border-white/[0.08] relative overflow-hidden`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-black/40 text-white/90 border border-white/[0.12] font-semibold">
                      {course.code}
                    </span>
                    <h2 className="text-lg font-bold text-white group-hover:text-indigo-300 transition-colors">
                      {course.name}
                    </h2>
                    <div className="flex items-center gap-2 text-xs text-white/80">
                      <span>{course.faculty}</span>
                      <span>·</span>
                      <span className="font-mono">{course.room}</span>
                    </div>
                  </div>

                  {/* Faculty Avatar Circle */}
                  <div className="w-10 h-10 rounded-full bg-white/10 border border-white/20 backdrop-blur-sm flex items-center justify-center text-xs font-mono font-bold text-white shrink-0">
                    {course.facultyAvatar}
                  </div>
                </div>

                {/* Exam Countdown Badge */}
                <div className="mt-3 flex items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1 font-medium">
                    <Clock className="w-3 h-3" /> ESE Exam: {course.examDate} ({course.examCountdown}d)
                  </span>
                </div>
              </div>

              {/* Card Body & Information */}
              <div className="p-4 space-y-3.5 flex-1 flex flex-col justify-between">
                <div className="space-y-3">
                  <p className="text-xs text-[#8A8F98] leading-relaxed line-clamp-2">
                    {course.description}
                  </p>

                  {/* Pending Assignment Alert */}
                  {course.pendingAssignment && (
                    <div
                      className={`p-2.5 rounded-lg border flex items-center justify-between gap-2 text-xs ${
                        course.pendingAssignment.isUrgent
                          ? "bg-rose-500/10 border-rose-500/25 text-rose-300"
                          : "bg-white/[0.04] border-white/[0.08] text-[#ECEEF0]"
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        {course.pendingAssignment.isUrgent ? (
                          <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-400" />
                        ) : (
                          <FileText className="w-3.5 h-3.5 shrink-0 text-[#8A8F98]" />
                        )}
                        <span className="font-medium truncate">{course.pendingAssignment.title}</span>
                      </div>
                      <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-black/40 shrink-0">
                        {course.pendingAssignment.dueDate}
                      </span>
                    </div>
                  )}

                  {/* Stats Bar */}
                  <div className="grid grid-cols-3 gap-2 pt-1 border-t border-white/[0.06] text-center text-xs text-[#8A8F98]">
                    <div className="p-1.5 rounded bg-[#121316]">
                      <span className="block font-mono text-white font-bold">{course.totalNotes}</span>
                      <span className="text-[10px]">Notes & Slides</span>
                    </div>
                    <div className="p-1.5 rounded bg-[#121316]">
                      <span className="block font-mono text-white font-bold">{course.totalAssignments}</span>
                      <span className="text-[10px]">Assignments</span>
                    </div>
                    <div className="p-1.5 rounded bg-[#121316]">
                      <span className="block font-mono text-white font-bold">{course.announcementCount}</span>
                      <span className="text-[10px]">Notices</span>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="pt-2 flex items-center gap-2.5">
                  <Link href={`/classroom/${course.id}`} className="flex-1">
                    <Button size="sm" variant="secondary" className="w-full" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                      Enter Room
                    </Button>
                  </Link>

                  <Link href={`/study?subject=${course.id}`} className="flex-1">
                    <Button
                      size="sm"
                      variant="primary"
                      className="w-full bg-[#5E6AD2] hover:bg-[#5E6AD2]/90"
                      icon={<Sparkles className="w-3.5 h-3.5" />}
                    >
                      Study Studio
                    </Button>
                  </Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </StudentLayout>
  );
}

