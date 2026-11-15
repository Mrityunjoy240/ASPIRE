"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  ClipboardList,
  ChevronLeft,
  CheckCircle2,
  XCircle,
  RefreshCw,
  ArrowRight,
  Trophy,
  Timer,
  BookOpen,
} from "lucide-react";

const QUIZ_SETS = [
  {
    id: "dbms-u3",
    subject: "CS501 — DBMS",
    title: "Unit 3: Normalization & FDs",
    questions: 5,
    duration: "10 min",
    difficulty: "Medium",
    color: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
    questions_data: [
      {
        q: "Which normal form guarantees both lossless join AND dependency preservation?",
        options: ["1NF", "2NF", "3NF", "BCNF"],
        correct: 2,
        why: "3NF always allows decomposition that is both lossless-join and dependency-preserving. BCNF cannot always preserve all functional dependencies.",
      },
      {
        q: "In BCNF, for every non-trivial FD X → Y, X must be a:",
        options: ["Candidate key only", "Superkey", "Primary key only", "Foreign key"],
        correct: 1,
        why: "BCNF requires the determinant X to be a superkey for every non-trivial functional dependency.",
      },
      {
        q: "Which DBMS component guarantees the Durability property of ACID?",
        options: ["Query Optimizer", "Recovery Manager / WAL", "Lock Manager", "Buffer Manager"],
        correct: 1,
        why: "The Recovery Manager uses Write-Ahead Logging (WAL) to ensure committed transactions survive system crashes.",
      },
      {
        q: "In a B+ tree, where are actual data record pointers stored?",
        options: ["Only root node", "All nodes equally", "Only in leaf nodes", "In index directory only"],
        correct: 2,
        why: "In B+ Trees, leaf nodes contain all key values with pointers to actual data records, linked as a doubly-linked list.",
      },
      {
        q: "What does Strict 2PL (Two-Phase Locking) guarantee?",
        options: [
          "Zero deadlocks",
          "Cascading abort prevention + strict serializability",
          "Zero lock conversions",
          "No shared locks needed",
        ],
        correct: 1,
        why: "Strict 2PL holds all exclusive locks until commit/abort, completely preventing cascading rollbacks.",
      },
    ],
  },
  {
    id: "os-u2",
    subject: "CS502 — OS",
    title: "Unit 2: Process Scheduling",
    questions: 5,
    duration: "8 min",
    difficulty: "Easy",
    color: "bg-violet-500/15 text-violet-300 border-violet-500/30",
    questions_data: [],
  },
  {
    id: "cn-u1",
    subject: "CS503 — Networks",
    title: "Unit 1: OSI & TCP/IP Model",
    questions: 5,
    duration: "10 min",
    difficulty: "Easy",
    color: "bg-sky-500/15 text-sky-300 border-sky-500/30",
    questions_data: [],
  },
  {
    id: "ai-u1",
    subject: "CS504 — AI & ML",
    title: "Unit 1: Search Algorithms",
    questions: 5,
    duration: "12 min",
    difficulty: "Hard",
    color: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    questions_data: [],
  },
];

export default function PracticeQuizzesPage() {
  const [selectedQuiz, setSelectedQuiz] = useState(QUIZ_SETS[0]);
  const [started, setStarted] = useState(false);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [submitted, setSubmitted] = useState(false);

  const quizData = selectedQuiz.questions_data;
  const score = quizData.filter((q, i) => answers[i] === q.correct).length;

  const handleSelect = (qi: number, ai: number) => {
    if (submitted) return;
    setAnswers((prev) => ({ ...prev, [qi]: ai }));
  };

  const handleReset = () => {
    setStarted(false);
    setAnswers({});
    setSubmitted(false);
  };

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
              <h1 className="text-xl font-bold text-white tracking-tight">Practice Quizzes</h1>
              <p className="text-xs text-[#8A8F98] mt-0.5">
                Unit-wise checkpoints grounded on <span className="text-white font-medium">BCREC syllabus</span>
              </p>
            </div>
          </div>
          {submitted && (
            <div
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-bold font-mono ${
                score >= 4
                  ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                  : score >= 3
                  ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
                  : "bg-rose-500/15 text-rose-300 border-rose-500/30"
              }`}
            >
              <Trophy className="w-4 h-4" /> Score: {score}/{quizData.length} ({Math.round((score / quizData.length) * 100)}%)
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left: Quiz Set Selector */}
          <div className="lg:col-span-4 space-y-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
              <ClipboardList className="w-3.5 h-3.5 text-[#5E6AD2]" /> Available Quizzes
            </span>
            <div className="space-y-2">
              {QUIZ_SETS.map((quiz) => {
                const isSelected = selectedQuiz.id === quiz.id;
                return (
                  <Card
                    key={quiz.id}
                    onClick={() => { setSelectedQuiz(quiz); handleReset(); }}
                    className={`p-4 cursor-pointer transition-all ${
                      isSelected
                        ? "border-[#5E6AD2] bg-[#121316] shadow-md shadow-indigo-500/10"
                        : "border-white/[0.08] hover:border-white/[0.14] bg-[#0D0E10]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${quiz.color}`}>
                        {quiz.difficulty}
                      </span>
                      <span className="text-[11px] text-[#8A8F98] flex items-center gap-1">
                        <Timer className="w-3 h-3" /> {quiz.duration}
                      </span>
                    </div>
                    <p className="text-xs font-semibold text-white">{quiz.title}</p>
                    <p className="text-[11px] text-[#8A8F98] mt-0.5">{quiz.subject} · {quiz.questions} questions</p>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Right: Quiz Canvas */}
          <div className="lg:col-span-8 space-y-4">
            {!started ? (
              /* Quiz Start Card */
              <Card className="p-6 bg-[#0D0E10] border-white/[0.08] text-center space-y-5">
                <div className={`w-16 h-16 rounded-2xl border mx-auto flex items-center justify-center ${selectedQuiz.color}`}>
                  <ClipboardList className="w-7 h-7" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">{selectedQuiz.title}</h2>
                  <p className="text-sm text-[#8A8F98] mt-1">{selectedQuiz.subject}</p>
                </div>
                <div className="flex items-center justify-center gap-6 text-xs text-[#8A8F98]">
                  <span className="flex items-center gap-1.5">
                    <ClipboardList className="w-3.5 h-3.5" /> {selectedQuiz.questions} Questions
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Timer className="w-3.5 h-3.5" /> {selectedQuiz.duration}
                  </span>
                  <span className={`font-mono px-2 py-0.5 rounded border ${selectedQuiz.color}`}>
                    {selectedQuiz.difficulty}
                  </span>
                </div>
                {selectedQuiz.questions_data.length > 0 ? (
                  <Button size="md" variant="primary" onClick={() => setStarted(true)} icon={<ArrowRight className="w-4 h-4" />}>
                    Start Quiz
                  </Button>
                ) : (
                  <div className="space-y-2">
                    <p className="text-xs text-[#8A8F98]">This quiz is coming soon. Try DBMS Unit 3 quiz for now.</p>
                    <Button size="md" variant="secondary" onClick={() => { setSelectedQuiz(QUIZ_SETS[0]); }}>
                      Load DBMS Quiz
                    </Button>
                  </div>
                )}
              </Card>
            ) : (
              /* Active Quiz */
              <div className="space-y-4">
                {/* Progress */}
                <div className="flex items-center justify-between text-xs text-[#8A8F98]">
                  <span>{selectedQuiz.title}</span>
                  <span>{Object.keys(answers).length}/{quizData.length} answered</span>
                </div>
                <div className="w-full h-1 bg-white/[0.08] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#5E6AD2] rounded-full transition-all"
                    style={{ width: `${(Object.keys(answers).length / quizData.length) * 100}%` }}
                  />
                </div>

                {/* Questions */}
                <div className="space-y-4">
                  {quizData.map((q, qi) => {
                    const sel = answers[qi];
                    return (
                      <Card key={qi} className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3">
                        <div className="flex items-start gap-2">
                          <span className="text-xs font-mono font-bold text-[#5E6AD2] mt-0.5">Q{qi + 1}.</span>
                          <p className="text-sm font-medium text-white leading-snug">{q.q}</p>
                        </div>
                        <div className="space-y-2">
                          {q.options.map((opt, ai) => {
                            let cls = "bg-[#0D0E10] text-[#ECEEF0] border-white/[0.06] hover:border-white/[0.14]";
                            if (sel === ai && !submitted) cls = "bg-[#5E6AD2]/20 text-white border-[#5E6AD2]";
                            if (submitted) {
                              if (ai === q.correct) cls = "bg-emerald-500/15 text-emerald-300 border-emerald-500/40";
                              else if (sel === ai) cls = "bg-rose-500/15 text-rose-300 border-rose-500/40";
                              else cls = "bg-[#0D0E10]/50 text-[#8A8F98] border-white/[0.04]";
                            }
                            return (
                              <button
                                key={ai}
                                onClick={() => handleSelect(qi, ai)}
                                disabled={submitted}
                                className={`w-full text-left text-xs p-2.5 rounded-lg border transition-all flex items-center justify-between ${cls}`}
                              >
                                <span>{opt}</span>
                                {submitted && ai === q.correct && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />}
                                {submitted && sel === ai && ai !== q.correct && <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />}
                              </button>
                            );
                          })}
                        </div>
                        {submitted && (
                          <div className="text-[11px] text-[#9DA3AE] bg-white/[0.03] p-2.5 rounded border border-white/[0.06]">
                            <span className="text-[10px] font-mono text-emerald-400 font-semibold uppercase block mb-0.5">Why:</span>
                            {q.why}
                          </div>
                        )}
                      </Card>
                    );
                  })}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-3">
                  {!submitted ? (
                    <Button
                      onClick={() => setSubmitted(true)}
                      disabled={Object.keys(answers).length < quizData.length}
                      className="flex-1"
                    >
                      Submit ({Object.keys(answers).length}/{quizData.length} answered)
                    </Button>
                  ) : (
                    <>
                      <Button variant="secondary" size="sm" onClick={handleReset} icon={<RefreshCw className="w-3.5 h-3.5" />}>
                        Retake
                      </Button>
                      <Link href="/plan" className="flex-1">
                        <Button variant="primary" size="sm" className="w-full" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                          Sync Score with Recovery Plan
                        </Button>
                      </Link>
                      <Link href="/study">
                        <Button variant="secondary" size="sm" icon={<BookOpen className="w-3.5 h-3.5" />}>
                          Study This Topic
                        </Button>
                      </Link>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </StudentLayout>
  );
}

