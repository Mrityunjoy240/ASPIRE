"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  BookOpen,
  Sparkles,
  ArrowRight,
  Clock,
  Calendar,
  FileText,
  Upload,
  User,
  GraduationCap,
  Layers,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ChevronLeft,
  MessageSquare,
  Paperclip,
  Send,
  Download,
} from "lucide-react";
import { CLASSROOM_COURSES } from "../classroom-data";

interface Announcement {
  id: string;
  author: string;
  role: string;
  date: string;
  content: string;
  attachments?: { name: string; size: string }[];
}

interface AssignmentItem {
  id: string;
  title: string;
  dueDate: string;
  points: number;
  status: "pending" | "submitted" | "graded";
  grade?: string;
  description: string;
  instructions: string[];
}

export default function SubjectClassroomPage() {
  const params = useParams();
  const courseId = (params?.id as string) || "cs501";
  const course = CLASSROOM_COURSES.find((c) => c.id === courseId) || CLASSROOM_COURSES[0];

  const [activeTab, setActiveTab] = useState<"stream" | "classwork" | "assignments">("stream");

  // Assignment submission mock state
  const [selectedAssignment, setSelectedAssignment] = useState<string>("a1");
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const ANNOUNCEMENTS: Announcement[] = [
    {
      id: "ann-1",
      author: course.faculty,
      role: "Faculty Lead",
      date: "12 Nov 2026, 10:30 AM",
      content: `Dear students of CSE Section A, the ESE Final Examination for ${course.name} is scheduled for ${course.examDate}. Unit 3 (Normalization) and Unit 4 (Transaction Processing) carry over 35 marks in Group B & C. Please review the updated slides and submit CA2 by tonight.`,
      attachments: [{ name: "Unit_3_Normalization_Final_Slides.pptx", size: "14.2 MB" }],
    },
    {
      id: "ann-2",
      author: course.faculty,
      role: "Faculty Lead",
      date: "08 Nov 2026, 02:15 PM",
      content: "Continuous Assessment 2 (CA2) assignment is now published. Students must complete questions 1-3 on Canonical Covers and 3NF/BCNF decomposition. Hand-written solutions scanned into PDF are accepted.",
    },
    {
      id: "ann-3",
      author: "Prof. Joyjit Patra",
      role: "Lab In-Charge",
      date: "04 Nov 2026, 11:00 AM",
      content: "Tomorrow's practical laboratory in Software Lab 3 will cover correlated subqueries and indexing execution plans. Bring your laptops with PostgreSQL or MySQL configured.",
    },
  ];

  const ASSIGNMENTS: AssignmentItem[] = [
    {
      id: "a1",
      title: "CA2: Normalization & Canonical Covers Problem Set",
      dueDate: "Tonight at 23:59",
      points: 25,
      status: isSubmitted ? "submitted" : "pending",
      description: "Solve the 3 given relational schemas: find all candidate keys using attribute closure, compute minimal canonical covers, and decompose into 3NF and BCNF.",
      instructions: [
        "Clearly show all attribute closures (e.g. (AB)+ step by step).",
        "State whether decomposition satisfies lossless-join and dependency-preservation.",
        "Upload a single PDF named: BCREC_CSE_2024_042_CA2.pdf",
      ],
    },
    {
      id: "a2",
      title: "Assignment 1: ER Model to Relational Schema Mapping",
      dueDate: "28 Oct 2026 (Closed)",
      points: 25,
      status: "graded",
      grade: "24 / 25",
      description: "Construct an ER diagram for a Hospital Blood Bank Management system with weak entities and ternary relationships, then map to SQL DDL statements.",
      instructions: ["Include primary key and foreign key constraints with ON DELETE CASCADE."],
    },
  ];

  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-[#8A8F98]">
          <Link href="/classroom" className="hover:text-white flex items-center gap-1">
            <ChevronLeft className="w-3.5 h-3.5" /> All Classrooms
          </Link>
          <span>/</span>
          <span className="text-white font-medium">{course.code} {course.name}</span>
        </div>

        {/* Google Classroom Style Hero Banner */}
        <div className={`rounded-2xl p-6 bg-gradient-to-r ${course.color} border ${course.accentBorder} relative overflow-hidden shadow-xl`}>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <span className="text-xs font-mono px-2.5 py-1 rounded bg-black/50 text-white border border-white/10 font-bold">
                {course.code} · CSE SEM 5
              </span>
              <h1 className="text-2xl font-bold text-white tracking-tight">{course.name}</h1>
              <p className="text-xs text-white/80">
                Instructor: <span className="font-semibold text-white">{course.faculty}</span> · Lecture Hall: {course.room}
              </p>
            </div>

            {/* NotebookLM Study Studio Launcher Button */}
            <div className="flex items-center gap-3 shrink-0">
              <Link href={`/study?subject=${course.id}`}>
                <Button
                  size="md"
                  variant="primary"
                  className="bg-[#5E6AD2] hover:bg-[#5E6AD2]/90 shadow-lg shadow-indigo-500/20 text-white font-bold flex items-center gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  Launch NotebookLM Study Studio
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Classroom Tabs: Stream, Classwork, Assignments */}
        <div className="flex items-center gap-1 p-1 bg-[#0D0E10] border border-white/[0.08] rounded-xl w-fit">
          <button
            onClick={() => setActiveTab("stream")}
            className={`px-4 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 ${
              activeTab === "stream"
                ? "bg-[#1C1D22] text-white border border-white/[0.12] shadow-sm"
                : "text-[#8A8F98] hover:text-white"
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" /> Stream & Notices ({ANNOUNCEMENTS.length})
          </button>
          <button
            onClick={() => setActiveTab("classwork")}
            className={`px-4 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 ${
              activeTab === "classwork"
                ? "bg-[#1C1D22] text-white border border-white/[0.12] shadow-sm"
                : "text-[#8A8F98] hover:text-white"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" /> Classwork & Notes ({course.totalNotes})
          </button>
          <button
            onClick={() => setActiveTab("assignments")}
            className={`px-4 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 ${
              activeTab === "assignments"
                ? "bg-[#1C1D22] text-white border border-white/[0.12] shadow-sm"
                : "text-[#8A8F98] hover:text-white"
            }`}
          >
            <FileText className="w-3.5 h-3.5" /> Assignments ({ASSIGNMENTS.length})
          </button>
        </div>

        {/* ======================================================== */}
        {/* TAB 1: STREAM & ANNOUNCEMENTS                            */}
        {/* ======================================================== */}
        {activeTab === "stream" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Quick Upcoming Deadlines (4 cols) */}
            <div className="lg:col-span-4 space-y-4">
              <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-rose-400" /> Upcoming Due Dates
                </span>

                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/25 space-y-1">
                  <span className="text-xs font-bold text-rose-300 block">CA2: Normalization Problem Set</span>
                  <p className="text-[11px] text-rose-300/80">Due Tonight at 23:59 · 25 Marks</p>
                  <button
                    onClick={() => setActiveTab("assignments")}
                    className="text-[11px] text-[#5E6AD2] hover:underline font-semibold block pt-1"
                  >
                    Go to Submission Drawer →
                  </button>
                </div>

                <div className="pt-2 border-t border-white/[0.06] text-xs text-[#8A8F98] space-y-1">
                  <span className="block font-medium text-white">ESE Semester Examination:</span>
                  <p className="font-mono text-amber-300">{course.examDate} ({course.examCountdown} days remaining)</p>
                </div>
              </Card>

              {/* Study Studio Mini CTA */}
              <Card className="p-4 bg-gradient-to-br from-indigo-950/30 to-[#0D0E10] border-indigo-500/30 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-white">
                  <Sparkles className="w-4 h-4 text-[#5E6AD2]" />
                  NotebookLM AI Studio
                </div>
                <p className="text-[11px] text-[#8A8F98] leading-relaxed">
                  Have doubts about the lecture slides or exam problems? Chat with your syllabus chunks and practice 5-mark proofs.
                </p>
                <Link href={`/study?subject=${course.id}`} className="block pt-1">
                  <Button size="sm" variant="primary" className="w-full bg-[#5E6AD2]">
                    Open Study Studio
                  </Button>
                </Link>
              </Card>
            </div>

            {/* Right Column: Faculty Announcements Feed (8 cols) */}
            <div className="lg:col-span-8 space-y-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">
                Classroom Announcements
              </span>

              <div className="space-y-4">
                {ANNOUNCEMENTS.map((ann) => (
                  <Card key={ann.id} className="p-5 bg-[#0D0E10] border-white/[0.08] space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-xs font-mono font-bold text-indigo-300">
                          {course.facultyAvatar}
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-white">{ann.author}</p>
                          <p className="text-[10px] text-[#8A8F98]">{ann.role}</p>
                        </div>
                      </div>
                      <span className="text-[11px] font-mono text-[#8A8F98]">{ann.date}</span>
                    </div>

                    <p className="text-xs text-[#ECEEF0] leading-relaxed whitespace-pre-line">
                      {ann.content}
                    </p>

                    {/* Attachments */}
                    {ann.attachments && (
                      <div className="pt-2 border-t border-white/[0.04]">
                        {ann.attachments.map((att, i) => (
                          <div
                            key={i}
                            className="p-2.5 rounded-lg bg-[#121316] border border-white/[0.06] flex items-center justify-between text-xs"
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <Paperclip className="w-3.5 h-3.5 text-[#5E6AD2] shrink-0" />
                              <span className="font-medium text-white truncate">{att.name}</span>
                              <span className="text-[10px] font-mono text-[#8A8F98]">({att.size})</span>
                            </div>
                            <Button size="sm" variant="secondary" icon={<Download className="w-3 h-3" />}>
                              Download
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB 2: CLASSWORK & NOTES                                 */}
        {/* ======================================================== */}
        {activeTab === "classwork" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">
                Syllabus Units & Lecture Repositories
              </span>
              <Link href={`/study?subject=${course.id}`}>
                <Button size="sm" variant="primary" icon={<Sparkles className="w-3.5 h-3.5" />}>
                  Study All Notes in AI Studio
                </Button>
              </Link>
            </div>

            <div className="space-y-3">
              {[
                { unit: 1, title: "ER Modeling, Schemas & Relational Algebra", weightage: "12 Marks", files: 3, status: "completed" },
                { unit: 2, title: "SQL, Nested Queries & Relational Calculus", weightage: "15 Marks", files: 2, status: "completed" },
                { unit: 3, title: "Relational Database Design & Normalization", weightage: "20 Marks", files: 4, status: "in-progress" },
                { unit: 4, title: "Transaction Processing, ACID & Concurrency (2PL)", weightage: "18 Marks", files: 3, status: "upcoming" },
                { unit: 5, title: "Physical Storage, File Organization & B+ Trees", weightage: "12 Marks", files: 2, status: "upcoming" },
              ].map((m) => (
                <Card key={m.unit} className="p-4 bg-[#0D0E10] border-white/[0.08] hover:border-white/[0.15] transition-all flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center font-mono font-bold text-xs text-indigo-300">
                      U{m.unit}
                    </span>
                    <div>
                      <h3 className="text-xs font-semibold text-white">{m.title}</h3>
                      <p className="text-[11px] text-[#8A8F98]">
                        Exam Weight: <span className="text-white font-medium">{m.weightage}</span> · {m.files} Files Available
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {m.status === "completed" && (
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
                        Completed ✓
                      </span>
                    )}
                    {m.status === "in-progress" && (
                      <span className="text-[10px] font-mono text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30 animate-pulse">
                        Active Target ⚡
                      </span>
                    )}
                    {m.status === "upcoming" && (
                      <span className="text-[10px] font-mono text-[#8A8F98] bg-white/[0.04] px-2 py-0.5 rounded">
                        Upcoming
                      </span>
                    )}
                    <Link href={`/study?subject=${course.id}`}>
                      <Button size="sm" variant="secondary" icon={<ExternalLink className="w-3 h-3" />}>
                        Open Notes
                      </Button>
                    </Link>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB 3: ASSIGNMENTS & SUBMISSION PORTAL                   */}
        {/* ======================================================== */}
        {activeTab === "assignments" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left: Assignment List (5 cols) */}
            <div className="lg:col-span-5 space-y-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">
                Course Assignments
              </span>

              <div className="space-y-3">
                {ASSIGNMENTS.map((asg) => {
                  const isSelected = selectedAssignment === asg.id;

                  return (
                    <Card
                      key={asg.id}
                      onClick={() => setSelectedAssignment(asg.id)}
                      className={`p-4 cursor-pointer transition-all space-y-2 ${
                        isSelected
                          ? "border-[#5E6AD2] bg-[#121316] shadow-md shadow-indigo-500/10"
                          : "border-white/[0.08] hover:border-white/[0.14] bg-[#0D0E10]"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white">{asg.title}</span>
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase font-semibold ${
                            asg.status === "submitted"
                              ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                              : asg.status === "graded"
                              ? "bg-sky-500/15 text-sky-300 border border-sky-500/30"
                              : "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                          }`}
                        >
                          {asg.status}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-[#8A8F98]">
                        <span>Due: {asg.dueDate}</span>
                        <span className="font-mono text-white font-medium">{asg.grade ? `Grade: ${asg.grade}` : `${asg.points} Points`}</span>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>

            {/* Right: Submission Workspace (7 cols) */}
            <div className="lg:col-span-7 space-y-4">
              {(() => {
                const asg = ASSIGNMENTS.find((a) => a.id === selectedAssignment) || ASSIGNMENTS[0];

                return (
                  <Card className="p-5 bg-[#0D0E10] border-white/[0.08] space-y-4">
                    <div className="pb-3 border-b border-white/[0.06] flex items-start justify-between gap-3">
                      <div>
                        <span className="text-[10px] font-mono text-[#5E6AD2] uppercase font-bold block">
                          Assignment Details & Instructions
                        </span>
                        <h2 className="text-base font-bold text-white mt-0.5">{asg.title}</h2>
                        <p className="text-xs text-[#8A8F98] mt-1">Due: {asg.dueDate} · Points: {asg.points}</p>
                      </div>

                      <span
                        className={`text-xs font-mono font-bold px-2.5 py-1 rounded ${
                          asg.status === "submitted"
                            ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                            : asg.status === "graded"
                            ? "bg-sky-500/15 text-sky-300 border border-sky-500/30"
                            : "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                        }`}
                      >
                        {asg.status.toUpperCase()}
                      </span>
                    </div>

                    <p className="text-xs text-[#ECEEF0] leading-relaxed">{asg.description}</p>

                    {/* Instructions list */}
                    <div className="p-3 rounded-lg bg-[#121316] border border-white/[0.06] space-y-1.5">
                      <span className="text-[11px] font-semibold text-[#8A8F98] uppercase tracking-wider block">
                        Submission Guidelines:
                      </span>
                      <ul className="space-y-1 text-xs text-[#ECEEF0]">
                        {asg.instructions.map((inst, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-[#5E6AD2] font-bold">•</span>
                            <span>{inst}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Drag and Drop File Upload Area */}
                    {asg.status !== "graded" && (
                      <div className="space-y-3 pt-2">
                        <span className="text-xs font-semibold text-white block">Your Work:</span>

                        {!isSubmitted ? (
                          <div className="border-2 border-dashed border-white/[0.14] hover:border-[#5E6AD2] rounded-xl p-6 text-center space-y-3 bg-[#121316]/50 transition-colors">
                            <Upload className="w-8 h-8 text-[#5E6AD2] mx-auto" />
                            <div>
                              <p className="text-xs font-semibold text-white">
                                {uploadedFile ? uploadedFile : "Drag & drop your solution PDF here"}
                              </p>
                              <p className="text-[11px] text-[#8A8F98]">Supported: .pdf, .docx, .zip (Max 25 MB)</p>
                            </div>

                            {!uploadedFile ? (
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => setUploadedFile("BCREC_CSE_2024_042_DBMS_CA2.pdf")}
                              >
                                Select File from Computer
                              </Button>
                            ) : (
                              <div className="flex items-center justify-center gap-2">
                                <span className="text-xs text-emerald-400 font-mono">File Attached ✓</span>
                                <Button size="sm" variant="primary" onClick={() => setIsSubmitted(true)}>
                                  Submit Assignment to Faculty
                                </Button>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-2">
                            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                            <h3 className="text-sm font-bold text-white">Successfully Submitted!</h3>
                            <p className="text-xs text-[#8A8F98]">
                              Submitted file: <span className="font-mono text-white">BCREC_CSE_2024_042_DBMS_CA2.pdf</span>
                            </p>
                            <Button size="sm" variant="secondary" onClick={() => setIsSubmitted(false)}>
                              Unsubmit / Resubmit File
                            </Button>
                          </div>
                        )}
                      </div>
                    )}
                  </Card>
                );
              })()}
            </div>
          </div>
        )}
      </div>
    </StudentLayout>
  );
}

