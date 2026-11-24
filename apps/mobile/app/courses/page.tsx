"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Sparkles,
} from "lucide-react";

interface CourseDetail {
  code: string;
  name: string;
  credits: number;
  faculty: string;
  units: { name: string; status: "completed" | "in-progress" | "upcoming" }[];
  ca1: number;
  ca2: number;
  assignments: { title: string; deadline: string; status: "submitted" | "pending" }[];
  slidesCount: number;
}

const COURSES_CATALOG: CourseDetail[] = [
  {
    code: "CS501",
    name: "Database Management Systems",
    credits: 4,
    faculty: "Prof. Raj Kumar Samanta",
    ca1: 21,
    ca2: 19,
    slidesCount: 64,
    units: [
      { name: "Unit 1: ER Modeling & Relational Algebra", status: "completed" },
      { name: "Unit 2: SQL, Nested Queries & Integrity", status: "completed" },
      { name: "Unit 3: Normalization & Functional Dependencies", status: "in-progress" },
      { name: "Unit 4: Transaction Processing & 2PL Concurrency", status: "upcoming" },
      { name: "Unit 5: Physical Storage & B+ Tree Indexing", status: "upcoming" },
    ],
    assignments: [
      { title: "Assignment 1: ER to Relational Mapping", deadline: "Submitted (24/25)", status: "submitted" },
      { title: "Assignment 2: BCNF Canonical Covers", deadline: "Due Tonight 23:59", status: "pending" },
    ],
  },
  {
    code: "CS502",
    name: "Operating Systems",
    credits: 4,
    faculty: "Dr. Anirban Bose",
    ca1: 23,
    ca2: 22,
    slidesCount: 48,
    units: [
      { name: "Unit 1: OS Structures & System Calls", status: "completed" },
      { name: "Unit 2: Process Scheduling & Threads", status: "completed" },
      { name: "Unit 3: Process Synchronization & Semaphores", status: "in-progress" },
      { name: "Unit 4: Memory Management & Paging", status: "upcoming" },
    ],
    assignments: [
      { title: "Assignment 1: CPU Scheduling Simulation", deadline: "Submitted (25/25)", status: "submitted" },
    ],
  },
  {
    code: "CS503",
    name: "Computer Networks",
    credits: 3,
    faculty: "Prof. Suman Dasgupta",
    ca1: 20,
    ca2: 21,
    slidesCount: 52,
    units: [
      { name: "Unit 1: OSI vs TCP/IP Architecture", status: "completed" },
      { name: "Unit 2: Data Link Layer & Sliding Window", status: "completed" },
      { name: "Unit 3: Routing Protocols (OSPF & BGP)", status: "in-progress" },
    ],
    assignments: [
      { title: "Assignment 1: Subnetting & IP Allocation", deadline: "Submitted (23/25)", status: "submitted" },
    ],
  },
  {
    code: "CS504",
    name: "Artificial Intelligence & ML",
    credits: 3,
    faculty: "Dr. Gour Sundar Mitra Thakur",
    ca1: 24,
    ca2: 24,
    slidesCount: 40,
    units: [
      { name: "Unit 1: Search Algorithms (A* & Minimax)", status: "completed" },
      { name: "Unit 2: Knowledge Representation", status: "in-progress" },
      { name: "Unit 3: Supervised Machine Learning", status: "upcoming" },
    ],
    assignments: [
      { title: "Assignment 1: Heuristic Search Implementation", deadline: "Submitted (25/25)", status: "submitted" },
    ],
  },
];

export default function CoursesPage() {
  const [selectedCourse, setSelectedCourse] = useState<CourseDetail>(COURSES_CATALOG[0]);

  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Courses, Notes & Assignments</h1>
            <p className="text-xs text-[#8A8F98] mt-0.5">
              Current Semester 5 Roster · 4 Theory + 2 Practical Courses (21 Credits Total)
            </p>
          </div>
          <Link href="/study">
            <Button size="md" variant="secondary" icon={<Sparkles className="w-3.5 h-3.5 text-[#5E6AD2]" />}>
              Open in AI Study Corner
            </Button>
          </Link>
        </div>

        {/* 2-Column Desktop Grid: Left Courses List (5 Cols), Right Course Details (7 Cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Courses Selector (5 Cols) */}
          <div className="lg:col-span-5 space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">
              Enrolled Courses (Autumn 2026)
            </span>

            <div className="space-y-2.5">
              {COURSES_CATALOG.map((course) => {
                const isSelected = selectedCourse.code === course.code;

                return (
                  <Card
                    key={course.code}
                    onClick={() => setSelectedCourse(course)}
                    className={`p-4 cursor-pointer transition-all ${
                      isSelected
                        ? "border-[#5E6AD2] bg-[#121316] shadow-md shadow-indigo-500/10"
                        : "border-white/[0.08] hover:border-white/[0.14] bg-[#0D0E10]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-semibold text-white truncate">{course.name}</span>
                      <span className="text-[10px] font-mono text-[#8A8F98] px-1.5 py-0.2 rounded bg-white/[0.04]">
                        {course.code}
                      </span>
                    </div>

                    <p className="text-xs text-[#8A8F98] mb-2">{course.faculty}</p>

                    <div className="flex items-center justify-between text-[11px] text-[#8A8F98] pt-2 border-t border-white/[0.06]">
                      <span>{course.credits} Credits</span>
                      <span className="font-mono text-white">CA1: {course.ca1}/25 · CA2: {course.ca2}/25</span>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Right Column: Selected Course Syllabus & Notes Workspace (7 Cols) */}
          <div className="lg:col-span-7 space-y-4">
            <Card className="p-5 bg-[#0D0E10] border-white/[0.08] space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-white/[0.06]">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-white">{selectedCourse.name}</h2>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-white/[0.06] text-white">
                      {selectedCourse.code}
                    </span>
                  </div>
                  <p className="text-xs text-[#8A8F98] mt-0.5">Faculty Lead: {selectedCourse.faculty}</p>
                </div>

                <Link href="/study">
                  <Button size="sm" variant="primary" icon={<Sparkles className="w-3 h-3" />}>
                    Chat with Syllabus
                  </Button>
                </Link>
              </div>

              {/* Units Roadmap */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-[#8A8F98] uppercase tracking-wider block">
                  Syllabus Modules & Lecture Notes:
                </span>

                <div className="space-y-2">
                  {selectedCourse.units.map((unit, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-[#121316] border border-white/[0.04] flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="text-xs font-mono font-bold text-[#5E6AD2]">M{idx + 1}</span>
                        <span className="font-medium text-white">{unit.name}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        {unit.status === "completed" && (
                          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/25">
                            Completed
                          </span>
                        )}
                        {unit.status === "in-progress" && (
                          <span className="text-[10px] font-mono text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/25">
                            In Progress
                          </span>
                        )}
                        {unit.status === "upcoming" && (
                          <span className="text-[10px] font-mono text-[#8A8F98] bg-white/[0.04] px-2 py-0.5 rounded">
                            Upcoming
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Assignments & Submissions */}
              <div className="space-y-2 pt-2 border-t border-white/[0.06]">
                <span className="text-xs font-semibold text-[#8A8F98] uppercase tracking-wider block">
                  Continuous Assessments & Assignments:
                </span>

                <div className="space-y-2">
                  {selectedCourse.assignments.map((asg, aIdx) => (
                    <div
                      key={aIdx}
                      className="p-3 rounded-lg bg-[#121316] border border-white/[0.04] flex items-center justify-between text-xs"
                    >
                      <div>
                        <div className="font-medium text-white">{asg.title}</div>
                        <div className="text-[11px] text-[#8A8F98]">{asg.deadline}</div>
                      </div>

                      <span
                        className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded ${
                          asg.status === "submitted"
                            ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                            : "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                        }`}
                      >
                        {asg.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </StudentLayout>
  );
}
