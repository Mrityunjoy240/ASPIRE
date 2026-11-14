"use client";

import React, { useState } from "react";
import Link from "next/link";
import { MobileLayout } from "@/components/MobileLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Sparkles,
  Send,
  CheckCircle2,
  XCircle,
  FileText,
  ArrowRight,
  RefreshCw,
} from "lucide-react";

interface QnA {
  id: string;
  question: string;
  answer: string;
  citation: string;
}

const PRESET_QUESTIONS: QnA[] = [
  {
    id: "q1",
    question: "Explain 3NF vs BCNF with a simple real-world example.",
    answer:
      "A table is in 3NF if for every functional dependency X → Y, either X is a superkey OR Y is a prime attribute. BCNF is stricter: X MUST be a superkey (no prime attribute exception).\n\n• Example: Consider Student-Advisor-Course where a student has one advisor per course, but advisors only teach one course. This is in 3NF, but violates BCNF because Advisor → Course holds even though Advisor is not a superkey by itself.\n• Fix: Decompose into (Advisor, Course) and (Student, Advisor).",
    citation: "BCREC MAKAUT CS501 · Unit 3: Relational Database Design, Page 42",
  },
  {
    id: "q2",
    question: "What are the ACID properties in database transactions?",
    answer:
      "1. Atomicity: All operations in a transaction succeed, or none do (All-or-Nothing via WAL/rollback).\n2. Consistency: Database moves from one valid state to another, preserving integrity constraints.\n3. Isolation: Concurrent transactions execute without interfering with each other (achieved via 2PL or MVCC).\n4. Durability: Once committed, changes persist even across power failures.",
    citation: "BCREC MAKAUT CS501 · Unit 4: Transaction Processing, Page 67",
  },
  {
    id: "q3",
    question: "What are the top 5 expected questions for BCREC DBMS End-Sem?",
    answer:
      "Based on past 3 years BCREC Autonomous papers:\n1. Prove that lossless-join and dependency-preservation decomposition is always achievable in 3NF.\n2. Explain Two-Phase Locking (2PL) protocol and prove how it guarantees serializability.\n3. Construct an ER diagram and map it to a relational schema for a Hospital Management System.\n4. Write SQL queries with correlated subqueries and aggregate GROUP BY HAVING clauses.\n5. Differentiate between B-Tree and B+ Tree indexing structures with search time complexity.",
    citation: "BCREC PYQ Analysis 2023–2025 · CSE 5th Semester",
  },
];

interface QuizQuestion {
  id: number;
  question: string;
  options: string[];
  correctIndex: number;
  explanation: string;
}

const MOCK_QUIZ: QuizQuestion[] = [
  {
    id: 1,
    question: "Which normal form guarantees both lossless join and dependency preservation?",
    options: ["1NF", "2NF", "3NF", "BCNF"],
    correctIndex: 2,
    explanation: "3NF always allows decomposition that is both lossless-join and dependency-preserving. BCNF cannot always preserve all functional dependencies.",
  },
  {
    id: 2,
    question: "In BCNF, for every non-trivial functional dependency X → Y, what must X be?",
    options: ["Candidate key only", "Superkey", "Primary key only", "Foreign key"],
    correctIndex: 1,
    explanation: "By definition, Boyee-Codd Normal Form requires the determinant X to be a superkey for every non-trivial functional dependency.",
  },
  {
    id: 3,
    question: "Which component of the DBMS guarantees the Durability property of ACID?",
    options: ["Query Optimizer", "Recovery Manager / Write-Ahead Log", "Lock Manager", "Buffer Manager"],
    correctIndex: 1,
    explanation: "The Recovery Manager uses Write-Ahead Logging (WAL) to ensure that all committed transactions survive system crashes.",
  },
  {
    id: 4,
    question: "What happens if a transaction follows Strict Two-Phase Locking (Strict 2PL)?",
    options: [
      "It prevents deadlocks completely",
      "It avoids cascading aborts and guarantees strict serializability",
      "It requires zero lock conversions",
      "It runs without shared locks",
    ],
    correctIndex: 1,
    explanation: "Strict 2PL holds all exclusive locks until the end of the transaction (Commit/Abort), completely preventing cascading rollbacks.",
  },
  {
    id: 5,
    question: "In a B+ tree of order p, where are the actual data record pointers stored?",
    options: [
      "Only in the root node",
      "In both internal nodes and leaf nodes",
      "Only in the leaf nodes",
      "In the index directory table only",
    ],
    correctIndex: 2,
    explanation: "In a B+ Tree, leaf nodes contain all key values along with pointers to actual data records, and are linked as a doubly-linked list.",
  },
];

export default function StudyCornerPage() {
  const [activeTab, setActiveTab] = useState<"chat" | "quiz">("chat");

  // Q&A State
  const [messages, setMessages] = useState<QnA[]>([PRESET_QUESTIONS[0]]);
  const [inputQuestion, setInputQuestion] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  // Quiz State
  const [userAnswers, setUserAnswers] = useState<Record<number, number>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);

  const handleSendQuestion = (text?: string) => {
    const qText = text || inputQuestion;
    if (!qText.trim()) return;

    // Check if preset matches or generate simulated intelligent answer grounded in syllabus
    const foundPreset = PRESET_QUESTIONS.find(
      (p) => p.question.toLowerCase().includes(qText.toLowerCase()) || qText.toLowerCase().includes(p.question.toLowerCase().slice(0, 15))
    );

    setIsTyping(true);
    setInputQuestion("");

    setTimeout(() => {
      if (foundPreset) {
        setMessages((prev) => [...prev, foundPreset]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: `q-${Date.now()}`,
            question: qText,
            answer: `Here is the concise explanation from your syllabus:\n\n• For "${qText}": In CS501 Database Management Systems, this corresponds to the relational integrity constraints and indexing rules.\n• Make sure to review canonical decomposition steps and candidate key closures.\n• This carries 5 marks in Group B of the BCREC MAKAUT semester paper.`,
            citation: "BCREC Syllabus Chunk · CS501 Unit 3: Normal Forms & Relational Decomposition",
          },
        ]);
      }
      setIsTyping(false);
    }, 600);
  };

  const handleSelectOption = (questionId: number, optionIndex: number) => {
    if (quizSubmitted) return;
    setUserAnswers((prev) => ({ ...prev, [questionId]: optionIndex }));
  };

  const calculateScore = () => {
    let score = 0;
    MOCK_QUIZ.forEach((q) => {
      if (userAnswers[q.id] === q.correctIndex) score += 1;
    });
    return score;
  };

  return (
    <MobileLayout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-white tracking-tight">AI Study Corner</h1>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                NotebookLM Grounded
              </span>
            </div>
            <p className="text-xs text-[#8A8F98]">
              Grounded on <span className="text-white font-medium">BCREC CS501 Syllabus Chunks</span> & Lecture Slides
            </p>
          </div>

          <div className="flex items-center gap-1 bg-[#121316] p-1 rounded-md border border-white/[0.08]">
            <button
              onClick={() => setActiveTab("chat")}
              className={`px-2.5 py-1 text-xs rounded font-medium transition-colors ${
                activeTab === "chat" ? "bg-[#5E6AD2] text-white" : "text-[#8A8F98] hover:text-white"
              }`}
            >
              Ask Syllabus
            </button>
            <button
              onClick={() => setActiveTab("quiz")}
              className={`px-2.5 py-1 text-xs rounded font-medium transition-colors flex items-center gap-1 ${
                activeTab === "quiz" ? "bg-[#5E6AD2] text-white" : "text-[#8A8F98] hover:text-white"
              }`}
            >
              Practice Quiz
            </button>
          </div>
        </div>

        {/* Tab 1: Chat with Syllabus */}
        {activeTab === "chat" && (
          <div className="space-y-3">
            {/* Quick Prompt Pills */}
            <div className="space-y-1.5">
              <span className="text-[11px] text-[#8A8F98] uppercase tracking-wider font-semibold">
                High-Yield Prompts:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {PRESET_QUESTIONS.map((preset) => (
                  <button
                    key={preset.id}
                    onClick={() => handleSendQuestion(preset.question)}
                    className="text-left text-[11px] px-2.5 py-1 rounded bg-[#121316] hover:bg-[#1C1D22] text-[#ECEEF0] border border-white/[0.08] hover:border-white/[0.15] transition-colors"
                  >
                    💡 {preset.question.slice(0, 38)}...
                  </button>
                ))}
              </div>
            </div>

            {/* Conversation Feed */}
            <div className="space-y-3 pt-1">
              {messages.map((item, idx) => (
                <div key={idx} className="space-y-2">
                  {/* User Question Bubble */}
                  <div className="flex justify-end">
                    <div className="bg-[#1C1D22] border border-white/[0.1] text-white text-xs px-3 py-2 rounded-lg max-w-[85%] font-medium">
                      {item.question}
                    </div>
                  </div>

                  {/* AI Grounded Answer Card */}
                  <Card className="p-3.5 space-y-2 bg-[#0D0E10] border-white/[0.08]">
                    <div className="flex items-center gap-1.5 text-[11px] text-[#5E6AD2] font-semibold">
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Syllabus Verified Answer</span>
                    </div>

                    <div className="text-xs text-[#ECEEF0] leading-relaxed whitespace-pre-line">
                      {item.answer}
                    </div>

                    <div className="pt-2 border-t border-white/[0.06] flex items-center gap-1.5 text-[10px] text-[#8A8F98] font-mono">
                      <FileText className="w-3 h-3 text-[#5E6AD2]" />
                      <span>{item.citation}</span>
                    </div>
                  </Card>
                </div>
              ))}

              {isTyping && (
                <div className="flex items-center gap-2 text-xs text-[#8A8F98] italic p-2">
                  <Sparkles className="w-3.5 h-3.5 animate-spin text-[#5E6AD2]" />
                  <span>Retrieving exact BCREC syllabus chunks...</span>
                </div>
              )}
            </div>

            {/* Input Bar */}
            <div className="sticky bottom-16 bg-[#08090A]/90 backdrop-blur-sm pt-2 pb-1">
              <div className="flex items-center gap-2 bg-[#121316] border border-white/[0.1] rounded-lg p-1.5 focus-within:border-[#5E6AD2] transition-colors">
                <input
                  type="text"
                  placeholder="Ask any doubt about DBMS or OS syllabus..."
                  value={inputQuestion}
                  onChange={(e) => setInputQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendQuestion()}
                  className="flex-1 bg-transparent text-xs text-white placeholder-[#6E7480] px-2 py-1 outline-none"
                />
                <Button
                  size="sm"
                  onClick={() => handleSendQuestion()}
                  disabled={!inputQuestion.trim()}
                  icon={<Send className="w-3 h-3" />}
                >
                  Ask
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Interactive Practice Quiz */}
        {activeTab === "quiz" && (
          <div className="space-y-4">
            <Card className="p-3 bg-gradient-to-r from-[#12131F] to-[#0D0E10] border-indigo-500/25 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-white">DBMS Unit 3 Checkpoint Quiz</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300">
                    5 Questions
                  </span>
                </div>
                <p className="text-[11px] text-[#8A8F98]">
                  Completing this quiz with ≥70% fulfills Day 2 of your Recovery Plan!
                </p>
              </div>

              {quizSubmitted && (
                <div className="text-right">
                  <div className="text-xs text-[#8A8F98]">Score</div>
                  <div className="font-mono text-base font-bold text-emerald-400">
                    {calculateScore()} / {MOCK_QUIZ.length}
                  </div>
                </div>
              )}
            </Card>

            {/* Questions List */}
            <div className="space-y-3">
              {MOCK_QUIZ.map((q, qIndex) => {
                const selectedOpt = userAnswers[q.id];

                return (
                  <Card key={q.id} className="p-3.5 space-y-2.5">
                    <div className="flex items-start gap-2">
                      <span className="text-xs font-mono font-bold text-[#5E6AD2]">Q{qIndex + 1}.</span>
                      <p className="text-xs font-medium text-white leading-snug">{q.question}</p>
                    </div>

                    {/* Options */}
                    <div className="space-y-1.5 pt-1">
                      {q.options.map((opt, optIndex) => {
                        let btnStyle = "bg-[#121316] text-[#ECEEF0] border-white/[0.08] hover:border-white/[0.15]";

                        if (selectedOpt === optIndex && !quizSubmitted) {
                          btnStyle = "bg-[#5E6AD2]/20 text-white border-[#5E6AD2]";
                        }

                        if (quizSubmitted) {
                          if (optIndex === q.correctIndex) {
                            btnStyle = "bg-emerald-500/15 text-emerald-300 border-emerald-500/40";
                          } else if (selectedOpt === optIndex) {
                            btnStyle = "bg-rose-500/15 text-rose-300 border-rose-500/40";
                          } else {
                            btnStyle = "bg-[#121316]/50 text-[#8A8F98] border-white/[0.04]";
                          }
                        }

                        return (
                          <button
                            key={optIndex}
                            onClick={() => handleSelectOption(q.id, optIndex)}
                            disabled={quizSubmitted}
                            className={`w-full text-left text-xs p-2.5 rounded-md border transition-all flex items-center justify-between ${btnStyle}`}
                          >
                            <span>{opt}</span>
                            {quizSubmitted && optIndex === q.correctIndex && (
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            )}
                            {quizSubmitted && selectedOpt === optIndex && optIndex !== q.correctIndex && (
                              <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                            )}
                          </button>
                        );
                      })}
                    </div>

                    {/* Explanation Reveal */}
                    {quizSubmitted && (
                      <div className="text-[11px] text-[#9DA3AE] bg-white/[0.03] p-2 rounded border border-white/[0.06] space-y-1">
                        <span className="text-[10px] font-mono text-emerald-400 font-semibold uppercase">
                          Explanation:
                        </span>
                        <p>{q.explanation}</p>
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>

            {/* Quiz Submit / Reset Buttons */}
            <div className="flex items-center justify-between pt-2">
              {!quizSubmitted ? (
                <Button
                  onClick={() => setQuizSubmitted(true)}
                  disabled={Object.keys(userAnswers).length < MOCK_QUIZ.length}
                  className="w-full"
                >
                  Submit Answers ({Object.keys(userAnswers).length}/{MOCK_QUIZ.length})
                </Button>
              ) : (
                <div className="flex items-center justify-between w-full gap-3">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setUserAnswers({});
                      setQuizSubmitted(false);
                    }}
                    icon={<RefreshCw className="w-3.5 h-3.5" />}
                  >
                    Retake Quiz
                  </Button>
                  <Link href="/plan" className="flex-1">
                    <Button variant="primary" className="w-full" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                      Mark Progress in Plan
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </MobileLayout>
  );
}
