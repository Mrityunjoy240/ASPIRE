"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  FileText,
  Download,
  ChevronLeft,
  BookOpen,
  Sparkles,
  ExternalLink,
} from "lucide-react";

const NOTES_LIBRARY = [
  {
    subject: "Database Management Systems",
    code: "CS501",
    faculty: "Prof. Raj Kumar Samanta",
    color: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
    files: [
      { name: "Unit 1 — ER Modeling & Relational Algebra", pages: 24, type: "PDF", updated: "Oct 12" },
      { name: "Unit 2 — SQL, Nested Queries & Integrity", pages: 31, type: "PDF", updated: "Oct 28" },
      { name: "Unit 3 — Normalization Slides", pages: 18, type: "PPTX", updated: "Nov 5" },
      { name: "Unit 4 — Transactions & Concurrency (Draft)", pages: 14, type: "PDF", updated: "Nov 10" },
    ],
  },
  {
    subject: "Operating Systems",
    code: "CS502",
    faculty: "Dr. Anirban Bose",
    color: "bg-violet-500/15 text-violet-300 border-violet-500/30",
    files: [
      { name: "Unit 1 — OS Structures & System Calls", pages: 20, type: "PDF", updated: "Oct 10" },
      { name: "Unit 2 — Process Scheduling & Threads", pages: 28, type: "PDF", updated: "Oct 25" },
      { name: "Unit 3 — Process Synchronization", pages: 22, type: "PDF", updated: "Nov 8" },
    ],
  },
  {
    subject: "Computer Networks",
    code: "CS503",
    faculty: "Prof. Suman Dasgupta",
    color: "bg-sky-500/15 text-sky-300 border-sky-500/30",
    files: [
      { name: "Unit 1 — OSI & TCP/IP Models", pages: 16, type: "PDF", updated: "Oct 8" },
      { name: "Unit 2 — Data Link Layer", pages: 19, type: "PDF", updated: "Oct 22" },
    ],
  },
  {
    subject: "Artificial Intelligence & ML",
    code: "CS504",
    faculty: "Dr. Gour Sundar Mitra Thakur",
    color: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    files: [
      { name: "Unit 1 — Search Algorithms & Heuristics", pages: 21, type: "PDF", updated: "Oct 14" },
      { name: "Unit 2 — Knowledge Representation", pages: 17, type: "PDF", updated: "Nov 1" },
    ],
  },
];

export default function LectureNotesPage() {
  const [selected, setSelected] = useState(NOTES_LIBRARY[0]);

  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link href="/study">
              <button className="p-1.5 rounded-md text-[#8A8F98] hover:text-white hover:bg-white/[0.06] transition-colors">
                <ChevronLeft className="w-4 h-4" />
              </button>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Lecture Notes Library</h1>
              <p className="text-xs text-[#8A8F98] mt-0.5">
                Faculty-uploaded notes · <span className="text-white font-medium">Semester 5, CSE</span>
              </p>
            </div>
          </div>
          <Link href="/study">
            <Button size="md" variant="secondary" icon={<Sparkles className="w-3.5 h-3.5 text-[#5E6AD2]" />}>
              Chat with Notes in AI Studio
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left: Subject List */}
          <div className="lg:col-span-4 space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">Your Subjects</span>
            <div className="space-y-2">
              {NOTES_LIBRARY.map((subj) => {
                const isSelected = selected.code === subj.code;
                return (
                  <Card
                    key={subj.code}
                    onClick={() => setSelected(subj)}
                    className={`p-4 cursor-pointer transition-all ${
                      isSelected
                        ? "border-[#5E6AD2] bg-[#121316] shadow-md shadow-indigo-500/10"
                        : "border-white/[0.08] hover:border-white/[0.14] bg-[#0D0E10]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${subj.color}`}>
                        {subj.code}
                      </span>
                      <span className="text-[11px] text-[#8A8F98]">{subj.files.length} files</span>
                    </div>
                    <p className="text-xs font-semibold text-white">{subj.subject}</p>
                    <p className="text-[11px] text-[#8A8F98] mt-0.5">{subj.faculty}</p>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Right: Notes for Selected Subject */}
          <div className="lg:col-span-8 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className={`text-[10px] font-mono px-2 py-1 rounded border ${selected.color}`}>
                  {selected.code}
                </span>
                <span className="text-sm font-semibold text-white">{selected.subject}</span>
              </div>
              <span className="text-xs text-[#8A8F98]">{selected.files.length} lecture note files</span>
            </div>

            <Card className="overflow-hidden border-white/[0.08]">
              <div className="divide-y divide-white/[0.04]">
                {selected.files.map((file, idx) => (
                  <div key={idx} className="p-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-md bg-white/[0.06] border border-white/[0.08] flex items-center justify-center">
                        <FileText className="w-4 h-4 text-[#5E6AD2]" />
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-white">{file.name}</p>
                        <p className="text-[11px] text-[#8A8F98]">{file.pages} pages · {file.type} · Updated {file.updated}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button size="sm" variant="secondary" icon={<ExternalLink className="w-3 h-3" />}>
                        View
                      </Button>
                      <Button size="sm" variant="secondary" icon={<Download className="w-3 h-3" />}>
                        Save
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* Chat CTA */}
            <Card className="p-4 border-indigo-500/25 bg-gradient-to-r from-[#12131F] to-[#0D0E10] flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-[#5E6AD2]" />
                <div>
                  <p className="text-sm font-semibold text-white">Ask AI about these notes</p>
                  <p className="text-[11px] text-[#8A8F98]">Get instant explanations, summaries, or exam-ready notes</p>
                </div>
              </div>
              <Link href="/study">
                <Button size="sm" variant="primary" icon={<BookOpen className="w-3.5 h-3.5" />}>
                  Open AI Study Studio
                </Button>
              </Link>
            </Card>
          </div>
        </div>
      </div>
    </StudentLayout>
  );
}

