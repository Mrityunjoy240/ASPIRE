"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  BookOpen,
  Sparkles,
  Send,
  Upload,
  XCircle,
  FileText,
  Layers,
  ArrowRight,
  Play,
  Pause,
  Download,
  Award,
  ChevronLeft,
  Plus,
  Paperclip,
  Volume2,
  FileCheck,
  Table,
} from "lucide-react";

// ==========================================
// DATA STRUCTURES
// ==========================================

interface SourceDoc {
  id: string;
  title: string;
  type: "faculty_slides" | "pyq" | "handout" | "student_notes";
  pages: number;
  uploadedDate: string;
  faculty: string;
  selected: boolean;
  contentSnippet: string;
}

interface VisualChatMessage {
  id: string;
  sender: "user" | "ai";
  text: string;
  timestamp: string;
  citations?: { title: string; page: number; snippet: string }[];
  // Intelligent UI extensions:
  visualType?: "schema_split" | "step_by_step" | "er_diagram" | "formula_card";
  schemaData?: {
    originalTable: { name: string; cols: string[]; fds: string[] };
    decomposedTables: { name: string; cols: string[]; primaryKey: string; isBCNF: boolean }[];
    lostDependency?: string;
  };
  stepperData?: {
    steps: { stepNumber: number; title: string; description: string; math: string }[];
    activeStep: number;
  };
  formulaData?: {
    formulaTitle: string;
    expression: string;
    proofLines: string[];
    examMarking: string;
  };
}

interface Flashcard {
  id: number;
  question: string;
  answer: string;
  hint?: string;
}

// ==========================================
// PRESET MOCK DATA
// ==========================================

const INITIAL_SOURCES: SourceDoc[] = [
  {
    id: "src-1",
    title: "Unit 3: Normalization & Relational Design Slides",
    type: "faculty_slides",
    pages: 64,
    uploadedDate: "05 Nov 2026",
    faculty: "Prof. Raj Kumar Samanta",
    selected: true,
    contentSnippet: "Boyce-Codd Normal Form requires every determinant to be a superkey. Unlike 3NF, BCNF does not allow exceptions for prime attributes.",
  },
  {
    id: "src-2",
    title: "BCREC Autonomous Solved PYQs (2023–2025)",
    type: "pyq",
    pages: 18,
    uploadedDate: "11 Nov 2026",
    faculty: "CSE Exam Cell",
    selected: true,
    contentSnippet: "Group B Q3(a): Given relation R(A,B,C,D,E) with F={A->BC, CD->E, B->D, E->A}. Decompose into BCNF. 5 Marks.",
  },
  {
    id: "src-3",
    title: "Unit 4: Transaction Processing & 2PL Handout",
    type: "handout",
    pages: 28,
    uploadedDate: "09 Nov 2026",
    faculty: "Prof. Raj Kumar Samanta",
    selected: true,
    contentSnippet: "Strict 2PL prevents cascading aborts by holding exclusive locks until the end of the transaction.",
  },
  {
    id: "src-4",
    title: "My Handwritten Lecture Notes (Nov 12).pdf",
    type: "student_notes",
    pages: 6,
    uploadedDate: "12 Nov 2026",
    faculty: "Ananya Roy (Self)",
    selected: false,
    contentSnippet: "Shortcut to compute canonical covers: always expand right side first before eliminating redundant attributes.",
  },
];

const PRESET_FLASHCARDS: Flashcard[] = [
  {
    id: 1,
    question: "What is the formal definition of 3NF?",
    answer: "For every non-trivial FD X → Y, either X is a superkey OR Y is a prime attribute.",
    hint: "Think about the prime attribute loophole.",
  },
  {
    id: 2,
    question: "Why is BCNF strictly stronger than 3NF?",
    answer: "BCNF strictly requires X to be a superkey for every non-trivial dependency X → Y. No exceptions for prime attributes.",
    hint: "No prime attribute allowance.",
  },
  {
    id: 3,
    question: "Can BCNF always preserve all functional dependencies?",
    answer: "No! Lossless join is guaranteed in both 3NF and BCNF, but dependency preservation is only guaranteed in 3NF.",
    hint: "Compare with 3NF guarantee.",
  },
  {
    id: 4,
    question: "What does Strict Two-Phase Locking (Strict 2PL) prevent?",
    answer: "Strict 2PL holds exclusive locks until commit/abort, completely preventing cascading rollbacks.",
    hint: "Prevents dirty reads.",
  },
];

export default function NotebookLMStudyRoomPage() {
  // Sources State (Left Column)
  const [sources, setSources] = useState<SourceDoc[]>(INITIAL_SOURCES);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [newSourceTitle, setNewSourceTitle] = useState("");

  // Citation Drawer Modal
  const [activeCitation, setActiveCitation] = useState<{ title: string; page: number; snippet: string } | null>(null);

  // Chat Canvas State (Middle Column)
  const [messages, setMessages] = useState<VisualChatMessage[]>([
    {
      id: "msg-welcome",
      sender: "ai",
      text: "Welcome to your NotebookLM Study Studio for CS501 Database Management Systems. I am grounded on your 3 selected professor slides and exam papers.\n\nAsk me any doubt or try one of the interactive visual breakdowns below:",
      timestamp: "10:00 AM",
      citations: [{ title: "Unit 3 Slides", page: 42, snippet: "Boyce-Codd Normal Form: for every X -> Y, X must be a superkey." }],
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  // Studio Tools State (Right Column)
  const [studioTool, setStudioTool] = useState<"audio" | "flashcards" | "cheat_sheet" | "quiz">("audio");
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [audioProgress, setAudioProgress] = useState(35); // 35% elapsed

  // Audio playback ticker
  useEffect(() => {
    if (!audioPlaying) return;
    const interval = setInterval(() => {
      setAudioProgress((prev) => (prev >= 100 ? 0 : prev + 1));
    }, 400);
    return () => clearInterval(interval);
  }, [audioPlaying]);

  // Flashcards flip state
  const [flippedCards, setFlippedCards] = useState<Record<number, boolean>>({});
  const [masteredCards, setMasteredCards] = useState<Record<number, boolean>>({});

  // Stepper active step state for interactive stepper in chat
  const [stepperStep, setStepperStep] = useState(1);

  const selectedCount = sources.filter((s) => s.selected).length;

  const toggleSource = (id: string) => {
    setSources((prev) =>
      prev.map((s) => (s.id === id ? { ...s, selected: !s.selected } : s))
    );
  };

  const handleAddSource = () => {
    if (!newSourceTitle.trim()) return;
    const newDoc: SourceDoc = {
      id: `src-${Date.now()}`,
      title: newSourceTitle.trim(),
      type: "student_notes",
      pages: 8,
      uploadedDate: "Just now",
      faculty: "Ananya Roy (Self)",
      selected: true,
      contentSnippet: "Custom student uploaded notes and revision formulas.",
    };
    setSources((prev) => [newDoc, ...prev]);
    setNewSourceTitle("");
    setShowUploadModal(false);
  };

  const handleSendPrompt = (presetText?: string, visualType?: "schema_split" | "step_by_step" | "formula_card") => {
    const text = presetText || inputPrompt;
    if (!text.trim()) return;

    const userMsg: VisualChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: text,
      timestamp: "Now",
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt("");
    setIsTyping(true);

    setTimeout(() => {
      let aiMsg: VisualChatMessage;

      if (visualType === "schema_split" || text.toLowerCase().includes("bcnf") || text.toLowerCase().includes("split")) {
        aiMsg = {
          id: `ai-${Date.now()}`,
          sender: "ai",
          text: "Here is the visual schema decomposition demonstrating why BCNF eliminates anomalies but can cause dependency loss on university exams:",
          timestamp: "Now",
          citations: [{ title: "Unit 3 Slides", page: 44, snippet: "Decomposition into BCNF: R(Student, Course, Instructor) where Inst -> Course." }],
          visualType: "schema_split",
          schemaData: {
            originalTable: {
              name: "Enrollment (Student, Course, Instructor)",
              cols: ["Student_ID (PK)", "Course_ID (PK)", "Instructor_Name"],
              fds: ["(Student, Course) → Instructor", "Instructor → Course"],
            },
            decomposedTables: [
              {
                name: "R1: Instructor_Course",
                cols: ["Instructor_Name (PK)", "Course_ID"],
                primaryKey: "Instructor_Name",
                isBCNF: true,
              },
              {
                name: "R2: Student_Instructor",
                cols: ["Student_ID (PK)", "Instructor_Name (PK)"],
                primaryKey: "(Student_ID, Instructor_Name)",
                isBCNF: true,
              },
            ],
            lostDependency: "(Student, Course) → Instructor is LOST across decomposed tables!",
          },
        };
      } else if (visualType === "step_by_step" || text.toLowerCase().includes("canonical") || text.toLowerCase().includes("step")) {
        aiMsg = {
          id: `ai-${Date.now()}`,
          sender: "ai",
          text: "Here is the interactive step-by-step algorithm for computing the Minimal Canonical Cover Fc:",
          timestamp: "Now",
          citations: [{ title: "BCREC PYQs 2024", page: 3, snippet: "Find Canonical Cover for F = {A -> BC, B -> C, A -> B}." }],
          visualType: "step_by_step",
          stepperData: {
            activeStep: 1,
            steps: [
              {
                stepNumber: 1,
                title: "Right-Hand Side Singleton Splitting",
                description: "Decompose compound right attributes so every FD has exactly one attribute on the right.",
                math: "A → BC decomposes into A → B and A → C.",
              },
              {
                stepNumber: 2,
                title: "Extraneous Left-Hand Attribute Elimination",
                description: "If an attribute on the left can be derived from the remaining attributes, delete it as extraneous.",
                math: "In AB → C, if (A)+ with respect to F contains C, then B is extraneous -> replace with A → C.",
              },
              {
                stepNumber: 3,
                title: "Redundant Dependency Removal",
                description: "For each FD X → Y, test if (X)+ with respect to (F - {X → Y}) still contains Y. If so, remove X → Y.",
                math: "Final Minimal Cover: Fc = {A → B, B → C}.",
              },
            ],
          },
        };
      } else if (text.toLowerCase().includes("2pl") || text.toLowerCase().includes("concurrency")) {
        aiMsg = {
          id: `ai-${Date.now()}`,
          sender: "ai",
          text: "In BCREC Group C (10 Marks), Strict Two-Phase Locking (Strict 2PL) is evaluated on two rules:\n\n1. Growing Phase: Locks acquired, none released.\n2. Shrinking Phase: All EXCLUSIVE locks must be held until COMMIT/ABORT.",
          timestamp: "Now",
          citations: [{ title: "Unit 4 Handout", page: 12, snippet: "Strict 2PL avoids cascading aborts and guarantees conflict serializability." }],
          visualType: "formula_card",
          formulaData: {
            formulaTitle: "Strict 2PL Serializability Theorem",
            expression: "Precedence Graph G(V, E) is strictly acyclic ⇒ Conflict Serializable & Cascade-Free",
            proofLines: [
              "Lock Point: The exact instant transaction acquires its final lock.",
              "Transactions serialize in the exact order of their Lock Points.",
              "Because exclusive locks are held until Commit, dirty reads are impossible.",
            ],
            examMarking: "10 Marks (3 Marks Definition, 4 Marks Proof, 3 Marks Timing Diagram)",
          },
        };
      } else {
        aiMsg = {
          id: `ai-${Date.now()}`,
          sender: "ai",
          text: `Grounded response based on ${selectedCount} selected sources:\n\n• For your question "${text}": In CS501 Database Management Systems, this corresponds to BCREC syllabus Unit 3 & 4.\n• Always begin your answer by defining the candidate key closure $(X)^+$.\n• This question has appeared in 2 of the last 3 years of autonomous semester papers.`,
          timestamp: "Now",
          citations: [{ title: "Unit 3 Slides", page: 42, snippet: "Relational database constraints and normalization algorithms." }],
        };
      }

      setMessages((prev) => [...prev, aiMsg]);
      setIsTyping(false);
    }, 500);
  };

  return (
    <StudentLayout>
      <div className="space-y-4">
        {/* Top Studio Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.08]">
          <div className="flex items-center gap-3">
            <Link href="/classroom/cs501">
              <button className="p-1.5 rounded-lg border border-white/[0.08] bg-[#121316] text-[#8A8F98] hover:text-white hover:border-white/[0.2] transition-colors flex items-center gap-1 text-xs">
                <ChevronLeft className="w-4 h-4" /> Exit to Classroom
              </button>
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold">
                  CS501 DBMS
                </span>
                <h1 className="text-base font-bold text-white tracking-tight">
                  NotebookLM AI Study Studio
                </h1>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold">
                  Grounded on {selectedCount} Sources
                </span>
              </div>
              <p className="text-[11px] text-[#8A8F98]">
                B.C. Roy Engineering College · Grounded on verified syllabus, slides & PYQs
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-rose-300 bg-rose-500/10 border border-rose-500/25 px-2.5 py-1 rounded font-medium">
              ESE Exam in 8 Days
            </span>
          </div>
        </div>

        {/* ======================================================== */}
        {/* 3-COLUMN DESKTOP NOTEBOOKLM WORKSPACE                    */}
        {/* ======================================================== */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* ====================================================== */}
          {/* LEFT COLUMN: SOURCES & NOTES PANEL (3 Cols)            */}
          {/* ====================================================== */}
          <div className="lg:col-span-3 space-y-3">
            <Card className="p-3.5 bg-[#0D0E10] border-white/[0.08] space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-[#5E6AD2]" /> Sources
                  </span>
                  <p className="text-[10px] text-[#8A8F98]">{selectedCount} of {sources.length} active in grounding</p>
                </div>

                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => setShowUploadModal(true)}
                  icon={<Plus className="w-3 h-3" />}
                >
                  Add
                </Button>
              </div>

              {/* Source Checklist */}
              <div className="space-y-2">
                {sources.map((src) => (
                  <div
                    key={src.id}
                    onClick={() => toggleSource(src.id)}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-all flex items-start gap-2.5 ${
                      src.selected
                        ? "bg-[#14151C] border-[#5E6AD2]/50 shadow-sm"
                        : "bg-[#101114] border-white/[0.04] opacity-60 hover:opacity-100"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={src.selected}
                      onChange={() => toggleSource(src.id)}
                      className="mt-0.5 rounded border-white/[0.2] accent-[#5E6AD2] cursor-pointer"
                    />

                    <div className="min-w-0 flex-1">
                      <p className={`text-xs font-medium truncate ${src.selected ? "text-white" : "text-[#8A8F98]"}`}>
                        {src.title}
                      </p>
                      <div className="flex items-center gap-1.5 text-[10px] text-[#8A8F98] mt-0.5">
                        <span
                          className={`font-mono uppercase px-1 rounded text-[9px] ${
                            src.type === "faculty_slides"
                              ? "bg-indigo-500/15 text-indigo-300"
                              : src.type === "pyq"
                              ? "bg-amber-500/15 text-amber-300"
                              : "bg-white/[0.06] text-[#ECEEF0]"
                          }`}
                        >
                          {src.type.replace("_", " ")}
                        </span>
                        <span>{src.pages} pgs</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Upload Extra Notes Action */}
              <button
                onClick={() => setShowUploadModal(true)}
                className="w-full py-2 border border-dashed border-white/[0.14] hover:border-[#5E6AD2] rounded-lg text-center text-xs text-[#8A8F98] hover:text-white transition-colors flex items-center justify-center gap-1.5"
              >
                <Upload className="w-3.5 h-3.5 text-[#5E6AD2]" /> Upload Extra Student Notes
              </button>
            </Card>

            {/* Quick High-Yield Query Chips */}
            <Card className="p-3.5 bg-[#0D0E10] border-white/[0.08] space-y-2">
              <span className="text-[10px] font-bold text-[#8A8F98] uppercase tracking-wider block">
                Visual Query Shortcuts:
              </span>
              <div className="space-y-1.5">
                <button
                  onClick={() => handleSendPrompt("Visualize 3NF vs BCNF schema split", "schema_split")}
                  className="w-full text-left p-2 rounded bg-[#121316] hover:bg-[#1C1D22] text-xs text-[#ECEEF0] border border-white/[0.04] transition-colors flex items-center justify-between"
                >
                  <span className="truncate">🎨 Schema Split (3NF vs BCNF)</span>
                  <ArrowRight className="w-3 h-3 text-[#5E6AD2] shrink-0" />
                </button>
                <button
                  onClick={() => handleSendPrompt("Step-by-step Canonical Cover algorithm", "step_by_step")}
                  className="w-full text-left p-2 rounded bg-[#121316] hover:bg-[#1C1D22] text-xs text-[#ECEEF0] border border-white/[0.04] transition-colors flex items-center justify-between"
                >
                  <span className="truncate">🪜 Step-by-Step Canonical Cover</span>
                  <ArrowRight className="w-3 h-3 text-[#5E6AD2] shrink-0" />
                </button>
                <button
                  onClick={() => handleSendPrompt("Explain Strict 2PL Concurrency proof", "formula_card")}
                  className="w-full text-left p-2 rounded bg-[#121316] hover:bg-[#1C1D22] text-xs text-[#ECEEF0] border border-white/[0.04] transition-colors flex items-center justify-between"
                >
                  <span className="truncate">📐 Strict 2PL 10-Mark Proof</span>
                  <ArrowRight className="w-3 h-3 text-[#5E6AD2] shrink-0" />
                </button>
              </div>
            </Card>
          </div>

          {/* ====================================================== */}
          {/* MIDDLE COLUMN: INTELLIGENT VISUAL CHAT CANVAS (5 Cols) */}
          {/* ====================================================== */}
          <div className="lg:col-span-5 space-y-3">
            <Card className="p-4 bg-[#0D0E10] border-white/[0.08] min-h-[600px] flex flex-col justify-between">
              {/* Messages Feed */}
              <div className="space-y-4 max-h-[520px] overflow-y-auto pr-1">
                {messages.map((msg) => (
                  <div key={msg.id} className="space-y-2">
                    {/* User Message */}
                    {msg.sender === "user" ? (
                      <div className="flex justify-end">
                        <div className="bg-[#1C1D22] text-white text-xs px-3.5 py-2.5 rounded-xl max-w-[85%] border border-white/[0.1] font-medium">
                          {msg.text}
                        </div>
                      </div>
                    ) : (
                      /* AI Message with Visual Extensions */
                      <div className="bg-[#121316] border border-white/[0.08] rounded-xl p-4 space-y-3">
                        <div className="flex items-center justify-between pb-1 border-b border-white/[0.04]">
                          <div className="flex items-center gap-1.5 text-xs text-[#5E6AD2] font-semibold">
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Grounded AI Companion</span>
                          </div>
                          <span className="text-[10px] font-mono text-[#8A8F98]">{msg.timestamp}</span>
                        </div>

                        <p className="text-xs text-[#ECEEF0] leading-relaxed whitespace-pre-line">
                          {msg.text}
                        </p>

                        {/* ============================================ */}
                        {/* VISUAL EXTENSION 1: INTERACTIVE SCHEMA SPLIT */}
                        {/* ============================================ */}
                        {msg.visualType === "schema_split" && msg.schemaData && (
                          <div className="p-3.5 rounded-lg bg-[#0A0B0D] border border-indigo-500/30 space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-[11px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                                <Table className="w-3.5 h-3.5 text-[#5E6AD2]" /> Relational Split Visualizer
                              </span>
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 font-semibold">
                                Lossy Dependency Warning
                              </span>
                            </div>

                            {/* Parent Table */}
                            <div className="p-2.5 rounded bg-[#14151C] border border-white/[0.06] space-y-1">
                              <span className="text-[10px] font-mono text-[#8A8F98] block">Original Schema (3NF):</span>
                              <p className="text-xs font-bold text-white">{msg.schemaData.originalTable.name}</p>
                              <div className="flex flex-wrap gap-1 pt-1">
                                {msg.schemaData.originalTable.cols.map((col, cIdx) => (
                                  <span key={cIdx} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-white">
                                    {col}
                                  </span>
                                ))}
                              </div>
                            </div>

                            {/* Split indicator arrow */}
                            <div className="flex items-center justify-center text-xs text-[#5E6AD2] font-mono font-bold">
                              ↓ Decomposes into BCNF Tables ↓
                            </div>

                            {/* Child Decomposed Tables */}
                            <div className="grid grid-cols-2 gap-2">
                              {msg.schemaData.decomposedTables.map((child, chIdx) => (
                                <div key={chIdx} className="p-2.5 rounded bg-[#121316] border border-emerald-500/30 space-y-1">
                                  <div className="flex items-center justify-between">
                                    <span className="text-xs font-bold text-white">{child.name}</span>
                                    <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-1 rounded">BCNF ✓</span>
                                  </div>
                                  <div className="space-y-0.5 text-[10px] font-mono text-[#8A8F98]">
                                    {child.cols.map((c, i) => (
                                      <div key={i} className="text-[#ECEEF0]">{c}</div>
                                    ))}
                                  </div>
                                </div>
                              ))}
                            </div>

                            {/* Lost Dependency Callout */}
                            {msg.schemaData.lostDependency && (
                              <div className="p-2 rounded bg-rose-500/10 border border-rose-500/25 text-[11px] text-rose-300 flex items-center gap-1.5">
                                <XCircle className="w-3.5 h-3.5 shrink-0" />
                                <span>{msg.schemaData.lostDependency}</span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* ============================================ */}
                        {/* VISUAL EXTENSION 2: INTERACTIVE STEPPER     */}
                        {/* ============================================ */}
                        {msg.visualType === "step_by_step" && msg.stepperData && (
                          <div className="p-3.5 rounded-lg bg-[#0A0B0D] border border-indigo-500/30 space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-[11px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                                <Layers className="w-3.5 h-3.5 text-[#5E6AD2]" /> Step-by-Step Algorithm
                              </span>
                              <div className="flex items-center gap-1">
                                {[1, 2, 3].map((st) => (
                                  <button
                                    key={st}
                                    onClick={() => setStepperStep(st)}
                                    className={`w-5 h-5 rounded-full text-[10px] font-mono flex items-center justify-center ${
                                      stepperStep === st
                                        ? "bg-[#5E6AD2] text-white font-bold"
                                        : "bg-white/[0.08] text-[#8A8F98]"
                                    }`}
                                  >
                                    {st}
                                  </button>
                                ))}
                              </div>
                            </div>

                            {/* Active Step Card */}
                            {(() => {
                              const cur = msg.stepperData.steps[stepperStep - 1] || msg.stepperData.steps[0];
                              return (
                                <div className="p-3 rounded-lg bg-[#14151C] border border-white/[0.06] space-y-1.5">
                                  <div className="flex items-center justify-between">
                                    <span className="text-xs font-bold text-white">
                                      Step {cur.stepNumber}: {cur.title}
                                    </span>
                                  </div>
                                  <p className="text-[11px] text-[#8A8F98] leading-relaxed">
                                    {cur.description}
                                  </p>
                                  <div className="p-2 rounded bg-black/40 border border-white/[0.04] font-mono text-[11px] text-emerald-300">
                                    {cur.math}
                                  </div>
                                </div>
                              );
                            })()}

                            <div className="flex items-center justify-between pt-1 text-xs">
                              <button
                                disabled={stepperStep <= 1}
                                onClick={() => setStepperStep((prev) => Math.max(1, prev - 1))}
                                className="text-[#8A8F98] hover:text-white disabled:opacity-30"
                              >
                                ← Prev Step
                              </button>
                              <button
                                disabled={stepperStep >= 3}
                                onClick={() => setStepperStep((prev) => Math.min(3, prev + 1))}
                                className="text-[#5E6AD2] hover:underline font-bold disabled:opacity-30"
                              >
                                Next Step →
                              </button>
                            </div>
                          </div>
                        )}

                        {/* ============================================ */}
                        {/* VISUAL EXTENSION 3: FORMULA & PROOF CARD    */}
                        {/* ============================================ */}
                        {msg.visualType === "formula_card" && msg.formulaData && (
                          <div className="p-3.5 rounded-lg bg-[#0A0B0D] border border-purple-500/30 space-y-2.5">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-white">{msg.formulaData.formulaTitle}</span>
                              <span className="text-[10px] font-mono text-purple-300 bg-purple-500/15 px-2 py-0.5 rounded font-semibold">
                                {msg.formulaData.examMarking}
                              </span>
                            </div>
                            <div className="p-2.5 rounded bg-[#14151C] font-mono text-xs text-amber-300 border border-amber-500/20">
                              {msg.formulaData.expression}
                            </div>
                            <div className="space-y-1 text-[11px] text-[#ECEEF0]">
                              {msg.formulaData.proofLines.map((line, plIdx) => (
                                <div key={plIdx} className="flex items-start gap-2">
                                  <span className="text-purple-400 font-bold">•</span>
                                  <span>{line}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Clickable Grounded Citations Drawer Trigger */}
                        {msg.citations && (
                          <div className="pt-2 border-t border-white/[0.04] flex flex-wrap items-center gap-1.5">
                            <span className="text-[10px] text-[#8A8F98] font-mono">Grounded In:</span>
                            {msg.citations.map((cit, cIdx) => (
                              <button
                                key={cIdx}
                                onClick={() => setActiveCitation(cit)}
                                className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/25 transition-colors flex items-center gap-1 cursor-pointer"
                              >
                                <FileCheck className="w-3 h-3 text-emerald-400" />
                                {cit.title} (p.{cit.page})
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {isTyping && (
                  <div className="flex items-center gap-2 p-2 text-xs text-[#8A8F98] italic">
                    <Sparkles className="w-3.5 h-3.5 text-[#5E6AD2] animate-spin" />
                    <span>Cross-verifying with {selectedCount} syllabus sources...</span>
                  </div>
                )}
              </div>

              {/* Chat Input Field */}
              <div className="pt-3 border-t border-white/[0.06] mt-2">
                <div className="flex items-center gap-2 bg-[#121316] border border-white/[0.1] rounded-xl p-2 focus-within:border-[#5E6AD2] transition-colors">
                  <input
                    type="text"
                    placeholder="Ask any question grounded on your selected notes..."
                    value={inputPrompt}
                    onChange={(e) => setInputPrompt(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSendPrompt()}
                    className="flex-1 bg-transparent text-xs text-white placeholder-[#6E7480] px-2 outline-none"
                  />
                  <Button
                    size="sm"
                    onClick={() => handleSendPrompt()}
                    disabled={!inputPrompt.trim()}
                    className="bg-[#5E6AD2]"
                    icon={<Send className="w-3 h-3" />}
                  >
                    Ask
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {/* ====================================================== */}
          {/* RIGHT COLUMN: NOTEBOOKLM STUDIO TOOLS (4 Cols)         */}
          {/* ====================================================== */}
          <div className="lg:col-span-4 space-y-4">
            {/* Tool Tabs */}
            <div className="flex items-center gap-1 p-1 bg-[#0D0E10] border border-white/[0.08] rounded-xl">
              <button
                onClick={() => setStudioTool("audio")}
                className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1 ${
                  studioTool === "audio"
                    ? "bg-[#1C1D22] text-white border border-white/[0.1]"
                    : "text-[#8A8F98] hover:text-white"
                }`}
              >
                <Volume2 className="w-3.5 h-3.5 text-amber-400" /> Audio
              </button>
              <button
                onClick={() => setStudioTool("flashcards")}
                className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1 ${
                  studioTool === "flashcards"
                    ? "bg-[#1C1D22] text-white border border-white/[0.1]"
                    : "text-[#8A8F98] hover:text-white"
                }`}
              >
                <Layers className="w-3.5 h-3.5 text-purple-400" /> Cards
              </button>
              <button
                onClick={() => setStudioTool("cheat_sheet")}
                className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1 ${
                  studioTool === "cheat_sheet"
                    ? "bg-[#1C1D22] text-white border border-white/[0.1]"
                    : "text-[#8A8F98] hover:text-white"
                }`}
              >
                <FileText className="w-3.5 h-3.5 text-sky-400" /> Cheat Sheet
              </button>
              <button
                onClick={() => setStudioTool("quiz")}
                className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1 ${
                  studioTool === "quiz"
                    ? "bg-[#1C1D22] text-white border border-white/[0.1]"
                    : "text-[#8A8F98] hover:text-white"
                }`}
              >
                <Award className="w-3.5 h-3.5 text-emerald-400" /> Quiz
              </button>
            </div>

            {/* TOOL 1: AUDIO OVERVIEW PODCAST PLAYER */}
            {studioTool === "audio" && (
              <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-amber-500/15 text-amber-300">
                      <Volume2 className="w-4 h-4" />
                    </span>
                    <div>
                      <h3 className="text-xs font-bold text-white">NotebookLM Audio Overview</h3>
                      <p className="text-[10px] text-[#8A8F98]">Generated 2-Host Study Discussion</p>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded font-semibold">
                    4m 12s
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-[#121316] border border-white/[0.06] space-y-2.5">
                  <span className="text-xs font-semibold text-white block">
                    Episode: "Why BCNF breaks Dependency Preservation (and how to answer on exam)"
                  </span>

                  {/* Audio Progress Bar */}
                  <div className="space-y-1">
                    <div className="w-full h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-amber-400 to-[#e6ba7e] transition-all"
                        style={{ width: `${audioProgress}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[10px] font-mono text-[#8A8F98]">
                      <span>
                        {String(Math.floor((audioProgress / 100 * 252) / 60)).padStart(2, "0")}:
                        {String(Math.floor((audioProgress / 100 * 252) % 60)).padStart(2, "0")}
                      </span>
                      <span>04:12</span>
                    </div>
                  </div>

                  {/* Controls */}
                  <div className="flex items-center justify-center gap-3 pt-1">
                    <button
                      onClick={() => setAudioPlaying(!audioPlaying)}
                      className="w-10 h-10 rounded-full bg-amber-400 hover:bg-amber-300 text-black flex items-center justify-center transition-colors shadow-md"
                    >
                      {audioPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                    </button>
                  </div>
                </div>

                {/* Audio Snippet Transcript */}
                <div className="p-3 rounded-lg bg-[#121316] border border-white/[0.04] space-y-1 text-xs text-[#ECEEF0]">
                  <span className="text-[10px] font-mono text-[#8A8F98] uppercase block">Preview Transcript:</span>
                  <p className="italic text-[11px] text-[#9d9b97]">
                    "Host 1: So Ananya, the professor always asks this in Group B. Why can't BCNF just preserve dependencies like 3NF? Host 2: Exactly! Because BCNF is uncompromising: every determinant MUST be a superkey..."
                  </p>
                </div>
              </Card>
            )}

            {/* TOOL 2: INTERACTIVE FLASHCARDS */}
            {studioTool === "flashcards" && (
              <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    Active Recall Deck
                  </span>
                  <span className="text-[10px] font-mono text-emerald-400">
                    {Object.values(masteredCards).filter(Boolean).length} / {PRESET_FLASHCARDS.length} Mastered
                  </span>
                </div>

                <div className="space-y-2.5">
                  {PRESET_FLASHCARDS.map((card, idx) => {
                    const isFlipped = !!flippedCards[card.id];
                    const isMastered = !!masteredCards[card.id];

                    return (
                      <div
                        key={card.id}
                        onClick={() =>
                          setFlippedCards((prev) => ({ ...prev, [card.id]: !prev[card.id] }))
                        }
                        className={`p-3 rounded-lg border cursor-pointer transition-all ${
                          isFlipped
                            ? "bg-[#181A22] border-indigo-500/40"
                            : "bg-[#121316] border-white/[0.06] hover:border-white/[0.14]"
                        }`}
                      >
                        <div className="flex items-center justify-between pb-1 border-b border-white/[0.04] text-[10px] font-mono text-[#8A8F98]">
                          <span>Card 0{idx + 1}</span>
                          <span className="text-[#5E6AD2]">{isFlipped ? "Answer ↷" : "Click to Flip ↺"}</span>
                        </div>

                        {!isFlipped ? (
                          <p className="text-xs font-semibold text-white pt-1">{card.question}</p>
                        ) : (
                          <div className="space-y-1 pt-1">
                            <p className="text-xs text-[#ECEEF0] leading-relaxed">{card.answer}</p>
                            <div className="pt-2 flex justify-end">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setMasteredCards((prev) => ({ ...prev, [card.id]: !prev[card.id] }));
                                }}
                                className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                                  isMastered
                                    ? "bg-emerald-500/20 text-emerald-300"
                                    : "bg-white/[0.08] text-white"
                                }`}
                              >
                                {isMastered ? "Mastered ✓" : "Mark Mastered"}
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </Card>
            )}

            {/* TOOL 3: 1-PAGE EXAM CHEAT SHEET */}
            {studioTool === "cheat_sheet" && (
              <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    1-Page Exam Cheat Sheet
                  </span>
                  <Button size="sm" variant="secondary" icon={<Download className="w-3 h-3" />}>
                    Save PDF
                  </Button>
                </div>

                <div className="p-3 rounded-lg bg-[#121316] border border-white/[0.06] space-y-2 text-xs">
                  <span className="font-bold text-white block">Normal Forms Quick Reference:</span>
                  <div className="space-y-1 font-mono text-[11px] text-[#ECEEF0]">
                    <div>• 1NF: Atomic attribute values only.</div>
                    <div>• 2NF: 1NF + No partial dependencies on candidate keys.</div>
                    <div>• 3NF: 2NF + For X → Y, either X is superkey OR Y is prime.</div>
                    <div>• BCNF: For every X → Y, X MUST be superkey (no prime exception).</div>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-[#121316] border border-white/[0.06] space-y-1 text-xs">
                  <span className="font-bold text-white block">Lossless-Join Theorem:</span>
                  <p className="font-mono text-[11px] text-amber-300">
                    Decomposition into R1 and R2 is lossless if (R1 ∩ R2) → (R1 - R2) OR (R1 ∩ R2) → (R2 - R1).
                  </p>
                </div>
              </Card>
            )}

            {/* TOOL 4: CHECKPOINT QUIZ */}
            {studioTool === "quiz" && (
              <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    5-Question Checkpoint
                  </span>
                  <span className="text-[10px] font-mono text-emerald-400">Target: ≥70%</span>
                </div>

                <div className="p-3 rounded-lg bg-[#121316] border border-white/[0.06] space-y-2 text-xs">
                  <p className="font-semibold text-white">Q1. Which normal form guarantees dependency preservation?</p>
                  <div className="space-y-1">
                    {["1NF", "2NF", "3NF", "BCNF"].map((opt, i) => (
                      <div
                        key={i}
                        className={`p-1.5 rounded text-xs border ${
                          i === 2
                            ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"
                            : "bg-[#0A0B0D] border-white/[0.04] text-[#8A8F98]"
                        }`}
                      >
                        {opt} {i === 2 && "✓ (Correct)"}
                      </div>
                    ))}
                  </div>
                </div>

                <Link href="/study/quizzes" className="block pt-1">
                  <Button size="sm" variant="primary" className="w-full bg-[#5E6AD2]">
                    Open Full Quiz Bank
                  </Button>
                </Link>
              </Card>
            )}
          </div>
        </div>

        {/* ======================================================== */}
        {/* CITATION SIDE DRAWER (Opens when citation is clicked)    */}
        {/* ======================================================== */}
        {activeCitation && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <Card className="max-w-md w-full p-5 bg-[#121316] border-indigo-500/40 space-y-3 shadow-2xl">
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.08]">
                <div className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-bold text-white">Verified Grounded Source</span>
                </div>
                <button
                  onClick={() => setActiveCitation(null)}
                  className="text-xs text-[#8A8F98] hover:text-white px-2 py-0.5 rounded bg-white/[0.06]"
                >
                  Close ✕
                </button>
              </div>

              <div>
                <h3 className="text-sm font-bold text-white">{activeCitation.title}</h3>
                <span className="text-[11px] font-mono text-[#5E6AD2]">Page {activeCitation.page} · Prof. Samanta Lecture Archive</span>
              </div>

              <div className="p-3.5 rounded-lg bg-[#0A0B0D] border border-white/[0.06] text-xs text-[#ECEEF0] leading-relaxed italic">
                "{activeCitation.snippet}"
              </div>

              <div className="pt-2 flex justify-end">
                <Button size="sm" variant="secondary" onClick={() => setActiveCitation(null)}>
                  Got It
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* ======================================================== */}
        {/* UPLOAD EXTRA SOURCE MODAL                                */}
        {/* ======================================================== */}
        {showUploadModal && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <Card className="max-w-md w-full p-5 bg-[#121316] border-white/[0.12] space-y-4 shadow-2xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Upload className="w-4 h-4 text-[#5E6AD2]" />
                  <h3 className="text-sm font-bold text-white">Upload Extra Student Notes</h3>
                </div>
                <button onClick={() => setShowUploadModal(false)} className="text-[#8A8F98] hover:text-white">
                  ✕
                </button>
              </div>

              <p className="text-xs text-[#8A8F98]">
                Add your own handwritten notes, PDFs, or lecture recordings. NotebookLM will index them and ground all answers on them.
              </p>

              <div>
                <label className="text-[11px] text-[#8A8F98] block mb-1">Source Title / Note Name:</label>
                <input
                  type="text"
                  placeholder="e.g. Unit 3 Handwritten Formula Summary.pdf"
                  value={newSourceTitle}
                  onChange={(e) => setNewSourceTitle(e.target.value)}
                  className="w-full bg-[#0D0E10] border border-white/[0.1] rounded-lg p-2 text-xs text-white outline-none focus:border-[#5E6AD2]"
                />
              </div>

              <div className="border-2 border-dashed border-white/[0.1] rounded-xl p-6 text-center space-y-2 bg-[#0A0B0D]">
                <Paperclip className="w-6 h-6 text-[#5E6AD2] mx-auto" />
                <p className="text-xs font-semibold text-white">Drag & drop your PDF or image here</p>
                <p className="text-[10px] text-[#8A8F98]">Supports PDF, DOCX, PNG (Max 50 MB)</p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.06]">
                <Button size="sm" variant="secondary" onClick={() => setShowUploadModal(false)}>
                  Cancel
                </Button>
                <Button size="sm" variant="primary" onClick={handleAddSource} disabled={!newSourceTitle.trim()}>
                  Add to Study Studio
                </Button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </StudentLayout>
  );
}
