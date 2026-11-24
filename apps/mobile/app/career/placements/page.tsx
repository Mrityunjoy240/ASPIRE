"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  CheckCircle2,
  AlertCircle,
  ChevronLeft,
  Star,
  Code2,
  Users,
  FileText,
  ExternalLink,
  Trophy,
  ArrowRight,
} from "lucide-react";

const COMPANIES = [
  {
    name: "Tata Consultancy Services",
    short: "TCS",
    color: "bg-blue-500/20 text-blue-300 border-blue-500/30",
    cgpa: 7.0,
    type: "Mass Recruiter",
    package: "3.6 LPA",
    roles: ["System Engineer", "Developer"],
    testPattern: "Cognitive + Programming + Communication",
    rounds: "Online Test → TR → HR",
    eligible: true,
    driveMonth: "Aug 2027",
  },
  {
    name: "Wipro",
    short: "WIP",
    color: "bg-violet-500/20 text-violet-300 border-violet-500/30",
    cgpa: 7.0,
    type: "Mass Recruiter",
    package: "3.5 LPA",
    roles: ["Project Engineer", "NLTH Elite"],
    testPattern: "AMCAT + Coding Test",
    rounds: "Online → TR → HR",
    eligible: true,
    driveMonth: "Sep 2027",
  },
  {
    name: "Capgemini",
    short: "CAP",
    color: "bg-sky-500/20 text-sky-300 border-sky-500/30",
    cgpa: 7.0,
    type: "Mass Recruiter",
    package: "4.0 LPA",
    roles: ["Analyst", "Senior Analyst"],
    testPattern: "Game-based Assessment + Coding",
    rounds: "Online → Group Discussion → TR → HR",
    eligible: true,
    driveMonth: "Aug 2027",
  },
  {
    name: "Accenture",
    short: "ACC",
    color: "bg-purple-500/20 text-purple-300 border-purple-500/30",
    cgpa: 7.5,
    type: "Mid-Tier",
    package: "4.5 LPA",
    roles: ["Associate Software Engineer"],
    testPattern: "Cognitive + Technical MCQ + Coding",
    rounds: "Online → Communication → TR → HR",
    eligible: true,
    driveMonth: "Sep 2027",
  },
  {
    name: "Amazon",
    short: "AMZ",
    color: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    cgpa: 8.0,
    type: "Dream Company",
    package: "12–24 LPA",
    roles: ["SDE-1", "SDE Intern"],
    testPattern: "2 Coding Problems (90 min) on HackerEarth",
    rounds: "Online OA → 4–5 Technical → Bar Raiser",
    eligible: true,
    driveMonth: "Nov 2026 (Intern) / Jul 2027",
  },
  {
    name: "Infosys",
    short: "INF",
    color: "bg-teal-500/20 text-teal-300 border-teal-500/30",
    cgpa: 6.5,
    type: "Mass Recruiter",
    package: "3.6 LPA",
    roles: ["Systems Engineer", "Digital Specialist"],
    testPattern: "Reasoning + Verbal + Coding",
    rounds: "Online → TR → HR",
    eligible: true,
    driveMonth: "Aug 2027",
  },
];

const RESUME_CHECKLIST = [
  { item: "CGPA on resume", tip: "8.21/10 — mention BCREC Autonomous board", done: true },
  { item: "Department rank", tip: "14/180 — this is impressive, include it!", done: true },
  { item: "NPTEL certifications listed", tip: "Python for DS + Cloud Computing — 4 credits", done: true },
  { item: "DSA project (GitHub link)", tip: "Create at least 1 public repo with README", done: false },
  { item: "DBMS mini-project", tip: "Hospital or Library DB schema + SQL queries PDF", done: false },
  { item: "Internship / Industrial visit", tip: "Even a 2-week online internship counts", done: false },
  { item: "Co-curricular activities", tip: "BCREC fests, hackathons, NSS — anything!", done: false },
  { item: "1-page format", tip: "No photo, clean ATS-friendly format, action verbs", done: true },
];

const DSA_ROADMAP = [
  { topic: "Arrays & Strings", problems: 25, done: 18, priority: "high" },
  { topic: "Linked Lists", problems: 15, done: 12, priority: "high" },
  { topic: "Stacks & Queues", problems: 10, done: 8, priority: "medium" },
  { topic: "Binary Trees & BST", problems: 20, done: 7, priority: "high" },
  { topic: "Dynamic Programming", problems: 30, done: 3, priority: "high" },
  { topic: "Graphs (BFS/DFS)", problems: 15, done: 2, priority: "medium" },
  { topic: "Sorting & Searching", problems: 10, done: 9, priority: "medium" },
];

export default function PlacementHubPage() {
  const [selectedCompany, setSelectedCompany] = useState(COMPANIES[0]);

  const resumeDone = RESUME_CHECKLIST.filter((r) => r.done).length;
  const totalDSA = DSA_ROADMAP.reduce((acc, t) => acc + t.problems, 0);
  const doneDSA = DSA_ROADMAP.reduce((acc, t) => acc + t.done, 0);

  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link href="/career">
              <button className="p-1.5 rounded-md text-[#8A8F98] hover:text-white hover:bg-white/[0.06] transition-colors">
                <ChevronLeft className="w-4 h-4" />
              </button>
            </Link>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold text-white tracking-tight">Placement Hub</h1>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold">
                  BCREC T&P 2027
                </span>
              </div>
              <p className="text-xs text-[#8A8F98] mt-0.5">
                On-campus placement drive ·{" "}
                <span className="text-white font-medium">Pre-registration opens Feb 2027</span>
              </p>
            </div>
          </div>
          <Button size="md" variant="secondary" icon={<FileText className="w-3.5 h-3.5 text-[#5E6AD2]" />}>
            Download Resume Template
          </Button>
        </div>

        {/* 3 Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4 space-y-1 bg-[#0D0E10] border-white/[0.08]">
            <div className="flex items-center justify-between text-xs text-[#8A8F98]">
              <span className="flex items-center gap-1.5"><Trophy className="w-3.5 h-3.5 text-amber-400" /> Eligible Companies</span>
            </div>
            <div className="text-3xl font-bold font-mono text-white">{COMPANIES.length}</div>
            <p className="text-[11px] text-emerald-300">All top recruiters at BCREC — eligible with CGPA 8.21</p>
          </Card>

          <Card className="p-4 space-y-1 bg-[#0D0E10] border-white/[0.08]">
            <div className="text-xs text-[#8A8F98] flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-[#5E6AD2]" /> Resume Readiness
            </div>
            <div className="text-3xl font-bold font-mono text-white">{resumeDone}/{RESUME_CHECKLIST.length}</div>
            <div className="w-full h-1.5 bg-white/[0.08] rounded-full overflow-hidden mt-1">
              <div
                className="h-full bg-indigo-500 rounded-full"
                style={{ width: `${(resumeDone / RESUME_CHECKLIST.length) * 100}%` }}
              />
            </div>
          </Card>

          <Card className="p-4 space-y-1 bg-[#0D0E10] border-white/[0.08]">
            <div className="text-xs text-[#8A8F98] flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5 text-[#5E6AD2]" /> DSA Progress
            </div>
            <div className="text-3xl font-bold font-mono text-white">{doneDSA}/{totalDSA}</div>
            <p className="text-[11px] text-[#8A8F98]">Problems solved · Target: 150 by Jan 2027</p>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left: Company List */}
          <div className="lg:col-span-4 space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-[#5E6AD2]" /> On-Campus Recruiters
            </span>
            <div className="space-y-2">
              {COMPANIES.map((co) => {
                const isSelected = selectedCompany.name === co.name;
                return (
                  <Card
                    key={co.name}
                    onClick={() => setSelectedCompany(co)}
                    className={`p-3.5 cursor-pointer transition-all ${
                      isSelected
                        ? "border-[#5E6AD2] bg-[#121316] shadow-md shadow-indigo-500/10"
                        : "border-white/[0.08] hover:border-white/[0.14] bg-[#0D0E10]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-8 h-8 rounded-md border flex items-center justify-center text-[11px] font-mono font-bold ${co.color}`}
                        >
                          {co.short}
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-white">{co.name}</p>
                          <p className="text-[11px] text-[#8A8F98]">{co.type} · {co.driveMonth}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="text-xs font-mono font-bold text-emerald-400">{co.package}</span>
                        <span className="block text-[10px] text-[#8A8F98]">CGPA ≥ {co.cgpa}</span>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Center: Company Detail */}
          <div className="lg:col-span-5 space-y-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98]">
              Company Deep Dive
            </span>
            <Card className="p-5 bg-[#0D0E10] border-white/[0.08] space-y-4">
              {/* Company Header */}
              <div className="flex items-start justify-between pb-3 border-b border-white/[0.06]">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-lg border flex items-center justify-center text-sm font-mono font-bold ${selectedCompany.color}`}
                  >
                    {selectedCompany.short}
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-white">{selectedCompany.name}</h2>
                    <p className="text-[11px] text-[#8A8F98]">{selectedCompany.type} · Drive: {selectedCompany.driveMonth}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-lg font-bold font-mono text-emerald-400">{selectedCompany.package}</span>
                  <span className="block text-[10px] text-[#8A8F98]">CTC Offered</span>
                </div>
              </div>

              {/* Eligibility */}
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/25">
                <div className="flex items-center gap-2 text-xs text-emerald-300 font-semibold">
                  <CheckCircle2 className="w-4 h-4" />
                  You are eligible for {selectedCompany.name}
                </div>
                <p className="text-[11px] text-emerald-300/70 mt-0.5">
                  Your CGPA 8.21 exceeds the minimum requirement of {selectedCompany.cgpa}
                </p>
              </div>

              {/* Roles */}
              <div className="space-y-1.5">
                <span className="text-[11px] font-semibold text-[#8A8F98] uppercase tracking-wider">Offered Roles</span>
                <div className="flex flex-wrap gap-1.5">
                  {selectedCompany.roles.map((role) => (
                    <span
                      key={role}
                      className="text-[11px] px-2.5 py-1 rounded bg-white/[0.06] border border-white/[0.08] text-white font-medium"
                    >
                      {role}
                    </span>
                  ))}
                </div>
              </div>

              {/* Test & Process */}
              <div className="space-y-2">
                <div className="p-3 rounded-lg bg-[#121316] border border-white/[0.06] space-y-1">
                  <span className="text-[11px] font-semibold text-[#8A8F98] uppercase tracking-wider block">Test Pattern</span>
                  <p className="text-xs text-[#ECEEF0]">{selectedCompany.testPattern}</p>
                </div>
                <div className="p-3 rounded-lg bg-[#121316] border border-white/[0.06] space-y-1">
                  <span className="text-[11px] font-semibold text-[#8A8F98] uppercase tracking-wider block">Interview Process</span>
                  <p className="text-xs text-[#ECEEF0]">{selectedCompany.rounds}</p>
                </div>
              </div>

              <Button variant="secondary" size="sm" icon={<ExternalLink className="w-3.5 h-3.5" />} className="w-full">
                View Past Questions & Resources
              </Button>
            </Card>
          </div>

          {/* Right: Resume Checklist */}
          <div className="lg:col-span-3 space-y-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
              <Star className="w-3.5 h-3.5 text-amber-400" /> Resume Checklist
            </span>
            <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-2.5">
              {RESUME_CHECKLIST.map((item, idx) => (
                <div key={idx} className="flex items-start gap-2.5">
                  {item.done ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-[#8A8F98] mt-0.5 shrink-0" />
                  )}
                  <div>
                    <p className={`text-xs font-medium ${item.done ? "text-white" : "text-[#9DA3AE]"}`}>
                      {item.item}
                    </p>
                    <p className="text-[11px] text-[#8A8F98] leading-relaxed">{item.tip}</p>
                  </div>
                </div>
              ))}
            </Card>

            {/* DSA Roadmap Mini */}
            <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
                <Code2 className="w-3.5 h-3.5 text-[#5E6AD2]" /> DSA Roadmap
              </span>
              <div className="space-y-2">
                {DSA_ROADMAP.map((topic, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-[#ECEEF0]">{topic.topic}</span>
                      <span className="font-mono text-[#8A8F98]">{topic.done}/{topic.problems}</span>
                    </div>
                    <div className="w-full h-1 bg-white/[0.08] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          topic.done / topic.problems >= 0.7
                            ? "bg-emerald-500"
                            : topic.done / topic.problems >= 0.4
                            ? "bg-amber-500"
                            : "bg-rose-500"
                        }`}
                        style={{ width: `${(topic.done / topic.problems) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <Link href="/study">
                <Button size="sm" variant="secondary" icon={<ArrowRight className="w-3 h-3" />} className="w-full mt-1">
                  Practice in AI Study Studio
                </Button>
              </Link>
            </Card>
          </div>
        </div>
      </div>
    </StudentLayout>
  );
}
