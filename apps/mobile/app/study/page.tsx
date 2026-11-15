"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  BookOpen,
  FileText,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Download,
  CheckCircle2,
  Clock,
  Search,
  Layers,
  Send,
  FileCheck,
  Award,
  Flame,
  ArrowRight,
  HelpCircle,
  ExternalLink,
} from "lucide-react";

// ==========================================
// DATA STRUCTURES
// ==========================================

interface NoteItem {
  id: string;
  title: string;
  type: "slides" | "handout" | "cheatsheet" | "pyq" | "assignment";
  pages: number;
  uploadedDate: string;
  faculty: string;
  summary: string;
  keyTakeaways: string[];
  examQuestions: {
    question: string;
    marks: number;
    answer: string;
  }[];
}

interface UnitModule {
  unitNumber: number;
  title: string;
  status: "completed" | "in-progress" | "upcoming";
  weightage: string;
  notes: NoteItem[];
}

interface SubjectDetail {
  id: string;
  code: string;
  name: string;
  faculty: string;
  totalUnits: number;
  completedUnits: number;
  totalNotes: number;
  examDate: string;
  examCountdownDays: number;
  criticalNotice?: string;
  accentColor: string;
  topics: string[];
  units: UnitModule[];
}

// ==========================================
// COURSE CATALOG & ACADEMIC REPOSITORY
// ==========================================

const SUBJECTS: SubjectDetail[] = [
  {
    id: "cs501",
    code: "CS501",
    name: "Database Management Systems",
    faculty: "Prof. Raj Kumar Samanta",
    totalUnits: 5,
    completedUnits: 2,
    totalNotes: 14,
    examDate: "23 Nov 2026",
    examCountdownDays: 8,
    criticalNotice: "ESE Final Exam in 8 days · Unit 3 & 4 carry 35 marks in Group B & C",
    accentColor: "border-indigo-500/40 text-indigo-400 bg-indigo-500/10",
    topics: ["ER & Relational Model", "SQL & Integrity", "3NF/BCNF Normalization", "2PL Concurrency", "B+ Trees"],
    units: [
      {
        unitNumber: 1,
        title: "ER Modeling, Schemas & Relational Algebra",
        status: "completed",
        weightage: "12 Marks",
        notes: [
          {
            id: "n-1-1",
            title: "Lecture 01-04: ER Diagrams to Relational Tables",
            type: "slides",
            pages: 28,
            uploadedDate: "14 Oct 2026",
            faculty: "Prof. Samanta",
            summary: "Comprehensive mapping rules from Entity-Relationship concepts to 1st normal form relational tables. Covers strong/weak entities, multi-valued attributes, composite attributes, and cardinality ratios.",
            keyTakeaways: [
              "Weak entity sets always require the primary key of their identifying strong entity set plus their partial key (discriminator).",
              "Multi-valued attributes MUST be split into a separate relation containing the entity primary key and the attribute value.",
              "1:N relationships store the primary key of the '1' side into the 'N' side table as a foreign key.",
            ],
            examQuestions: [
              {
                question: "Explain the algorithm to convert an ER diagram with weak entities and ternary relationships into tables.",
                marks: 5,
                answer: "1. Strong Entities: Create a table with all atomic attributes, primary key unchanged.\n2. Weak Entities: Create table with discriminator + primary key of owner entity as composite primary key.\n3. Ternary Relationship: Create table with primary keys of all three participating entities as composite key, plus any descriptive attributes.",
              },
            ],
          },
          {
            id: "n-1-2",
            title: "Relational Algebra Operations & Query Trees",
            type: "cheatsheet",
            pages: 6,
            uploadedDate: "20 Oct 2026",
            faculty: "Prof. Samanta",
            summary: "Formal relational operators: Selection (σ), Projection (π), Cartesian Product (×), Natural Join (⋈), Division (÷), and Set operations.",
            keyTakeaways: [
              "Selection σ is commutative: σ_p1(σ_p2(R)) = σ_p2(σ_p1(R)).",
              "Projection π is NOT commutative.",
              "Natural join R ⋈ S equates attributes with identical names and eliminates duplicates.",
            ],
            examQuestions: [
              {
                question: "Express the Division (÷) operator using fundamental relational algebra operators.",
                marks: 5,
                answer: "R ÷ S = π_(R-S)(R) - π_(R-S)((π_(R-S)(R) × S) - R). It returns tuples in R(A, B) that are associated with ALL tuples in S(B).",
              },
            ],
          },
        ],
      },
      {
        unitNumber: 2,
        title: "SQL, Nested Queries, Views & Constraints",
        status: "completed",
        weightage: "15 Marks",
        notes: [
          {
            id: "n-2-1",
            title: "Advanced SQL: Correlated Subqueries & GROUP BY HAVING",
            type: "handout",
            pages: 22,
            uploadedDate: "27 Oct 2026",
            faculty: "Prof. Samanta",
            summary: "Deep dive into SQL aggregation, subqueries evaluated row-by-row (correlated), and difference between WHERE and HAVING filters.",
            keyTakeaways: [
              "WHERE filters individual rows before grouping; HAVING filters aggregated groups.",
              "Correlated subqueries refer to attributes from the outer query and execute once per candidate row.",
              "Integrity constraints include NOT NULL, UNIQUE, PRIMARY KEY, FOREIGN KEY (ON DELETE CASCADE), and CHECK.",
            ],
            examQuestions: [
              {
                question: "Write an SQL query to find the 2nd highest salary from an Employee table without using LIMIT/TOP.",
                marks: 5,
                answer: "SELECT MAX(salary) FROM Employee WHERE salary < (SELECT MAX(salary) FROM Employee); OR: SELECT salary FROM Employee E1 WHERE 1 = (SELECT COUNT(DISTINCT salary) FROM Employee E2 WHERE E2.salary > E1.salary);",
              },
            ],
          },
        ],
      },
      {
        unitNumber: 3,
        title: "Relational Database Design & Normalization",
        status: "in-progress",
        weightage: "20 Marks",
        notes: [
          {
            id: "n-3-1",
            title: "Unit 3 Official Slides: Normal Forms & Functional Dependencies",
            type: "slides",
            pages: 64,
            uploadedDate: "05 Nov 2026",
            faculty: "Prof. Samanta",
            summary: "Armstrong's axioms, closure of functional dependencies (F+), canonical cover, and formal conditions for 1NF, 2NF, 3NF, and BCNF.",
            keyTakeaways: [
              "3NF condition: For X → Y, either X is a superkey OR Y is a prime attribute.",
              "BCNF condition: For X → Y, X MUST be a superkey. There is no prime attribute exception.",
              "Lossless-join decomposition is ALWAYS achievable in both 3NF and BCNF.",
              "Dependency-preservation is GUARANTEED in 3NF, but NOT always possible in BCNF.",
            ],
            examQuestions: [
              {
                question: "Differentiate between 3NF and BCNF with a concrete example where 3NF holds but BCNF is violated.",
                marks: 5,
                answer: "3NF allows X → Y if Y is a prime attribute even when X is not superkey. BCNF strictly forbids this.\n\nExample: R(Student, Course, Instructor). A student has one instructor per course, but instructors teach only one course.\nFDs: (Student, Course) → Instructor, Instructor → Course.\nCandidate keys: (Student, Course) and (Student, Instructor).\nIn Instructor → Course: Course is prime attribute, so it is in 3NF! But Instructor is NOT superkey, so it VIOLATES BCNF.",
              },
              {
                question: "Explain the algorithm to compute the Canonical Cover Fc of a set of functional dependencies.",
                marks: 5,
                answer: "1. Right-side decomposition: Split X → Y1Y2 into X → Y1 and X → Y2.\n2. Left-side extraneous attribute removal: If attribute A in X is extraneous (i.e. (X - {A})+ with respect to F contains Y), replace X → Y with (X - {A}) → Y.\n3. Redundant dependency removal: If F - {X → Y} logically implies X → Y, delete it.",
              },
            ],
          },
          {
            id: "n-3-2",
            title: "Exam 1-Pager: 3NF vs BCNF Comparison & Formula Cheat Sheet",
            type: "cheatsheet",
            pages: 4,
            uploadedDate: "09 Nov 2026",
            faculty: "Prof. Samanta",
            summary: "High-yield summary card specifically formatted for BCREC autonomous semester papers. Quick tests for candidate keys and decomposition.",
            keyTakeaways: [
              "Quick test for lossless join: R1 ∩ R2 must determine (R1 - R2) or (R2 - R1).",
              "Number of candidate keys calculation using attribute closure.",
              "Anomalies eliminated: Insertion, Deletion, and Modification.",
            ],
            examQuestions: [
              {
                question: "State and prove the condition for lossless-join decomposition of relation R into R1 and R2.",
                marks: 5,
                answer: "Theorem: Decomposition is lossless if and only if (R1 ∩ R2) → R1 or (R1 ∩ R2) → R2 in F+.\nProof outline: Let common attributes be C = R1 ∩ R2. If C → R1, then C is a superkey of R1. By Chase algorithm, any row matching on C can be uniquely reconstructed.",
              },
            ],
          },
          {
            id: "n-3-3",
            title: "BCREC Past 3 Years Solved Normalization PYQs (2023-2025)",
            type: "pyq",
            pages: 14,
            uploadedDate: "11 Nov 2026",
            faculty: "CSE Academic Cell",
            summary: "Past year university exam questions on finding candidate keys, decomposing relations, and testing normal forms.",
            keyTakeaways: [
              "Question 3(a) in 2023, 2024, and 2025 was a 5-mark decomposition problem.",
              "Always write: Step 1: Attribute closure, Step 2: Candidate keys, Step 3: Test each FD, Step 4: Decompose.",
            ],
            examQuestions: [
              {
                question: "Given R(A, B, C, D, E) with F = {A → BC, CD → E, B → D, E → A}. Find all candidate keys and the highest normal form.",
                marks: 5,
                answer: "1. (A)+ = {A, B, C, D, E} → A is a candidate key.\n2. Since E → A, (E)+ contains all attributes → E is candidate key.\n3. Since CD → E, (CD)+ = {C, D, E, A, B} → CD is candidate key.\n4. Since B → D, (BC)+ = {B, C, D, E, A} → BC is candidate key.\nCandidate keys: {A, E, CD, BC}.\nIn B → D: B is not superkey, D is not prime (prime = {A, E, C, D, B} -> wait, D is prime!). All attributes are prime, so R is in 3NF. But B is not superkey, so not in BCNF.",
              },
            ],
          },
        ],
      },
      {
        unitNumber: 4,
        title: "Transaction Processing, ACID & Concurrency Control (2PL)",
        status: "upcoming",
        weightage: "18 Marks",
        notes: [
          {
            id: "n-4-1",
            title: "Transaction States, ACID Properties & Serializability",
            type: "slides",
            pages: 36,
            uploadedDate: "12 Nov 2026",
            faculty: "Prof. Samanta",
            summary: "Atomicity, Consistency, Isolation, Durability. Conflict vs View Serializability, Precedence Graph (Serialization Graph) cycle detection.",
            keyTakeaways: [
              "Conflict Serializability: If the precedence graph has NO cycles, the schedule is conflict serializable.",
              "Strict 2PL prevents cascading rollbacks and guarantees conflict serializability.",
              "Deadlock handling: Wait-Die vs Wound-Wait timestamp strategies.",
            ],
            examQuestions: [
              {
                question: "Explain Two-Phase Locking (2PL) protocol. How does Strict 2PL differ from Basic 2PL?",
                marks: 5,
                answer: "Basic 2PL has two phases: Growing phase (locks acquired, no locks released) and Shrinking phase (locks released, no locks acquired).\nStrict 2PL: All exclusive (X) locks held by transaction are retained until Commit or Abort. This guarantees freedom from cascading aborts.",
              },
            ],
          },
        ],
      },
      {
        unitNumber: 5,
        title: "Physical Storage, File Organization & B+ Tree Indexing",
        status: "upcoming",
        weightage: "12 Marks",
        notes: [
          {
            id: "n-5-1",
            title: "Indexing Structures: Dense vs Sparse, B-Tree vs B+ Tree",
            type: "slides",
            pages: 32,
            uploadedDate: "13 Nov 2026",
            faculty: "Prof. Samanta",
            summary: "Single-level and multi-level indexing, Clustered vs Non-clustered, B+ Tree search, insertion with node splits, and deletion with merges.",
            keyTakeaways: [
              "B+ Trees store actual data pointers ONLY at leaf nodes, leaving internal nodes purely for routing keys.",
              "Leaf nodes in a B+ Tree are linked sequentially via pointers, making range queries O(log N + k).",
              "Height of B+ Tree of order p with N records is ceil(log_(p/2)(N)).",
            ],
            examQuestions: [
              {
                question: "Why are B+ Trees preferred over B-Trees for database disk storage?",
                marks: 5,
                answer: "1. Higher Fanout: Since internal nodes do not store data pointers, more keys fit per disk page, reducing tree height.\n2. Faster Range Searches: Leaf nodes form a linked list, so range scans do not require tree traversal.\n3. Predictable Search Time: All leaf nodes are at identical depth.",
              },
            ],
          },
        ],
      },
    ],
  },
  {
    id: "cs502",
    code: "CS502",
    name: "Operating Systems",
    faculty: "Dr. Anirban Bose",
    totalUnits: 4,
    completedUnits: 2,
    totalNotes: 11,
    examDate: "28 Nov 2026",
    examCountdownDays: 13,
    accentColor: "border-violet-500/40 text-violet-400 bg-violet-500/10",
    topics: ["System Calls & Structures", "CPU Scheduling (FCFS/RR/SJF)", "Process Synchronization & Semaphores", "Memory Paging & Virtual Memory"],
    units: [
      {
        unitNumber: 1,
        title: "OS Architecture, Dual-Mode & System Calls",
        status: "completed",
        weightage: "10 Marks",
        notes: [
          {
            id: "n-os-1",
            title: "Dual Mode Operation, Kernel vs User Mode & Syscalls",
            type: "slides",
            pages: 24,
            uploadedDate: "10 Oct 2026",
            faculty: "Dr. Bose",
            summary: "Hardware protection, privilege levels (Ring 0 vs Ring 3), trap handling, interrupt vectors, and fork(), exec(), wait() calls in Unix.",
            keyTakeaways: ["Mode bit transitions from 1 (user) to 0 (kernel) on software interrupt (trap).", "fork() returns 0 in child process and child PID in parent process."],
            examQuestions: [{ question: "Explain the dual-mode operation in modern OS with hardware support.", marks: 5, answer: "Dual mode separates User Mode (mode bit 1) and Kernel Mode (mode bit 0). Privileged instructions can only execute in kernel mode." }],
          },
        ],
      },
      {
        unitNumber: 2,
        title: "Process Scheduling & Threads",
        status: "completed",
        weightage: "18 Marks",
        notes: [
          {
            id: "n-os-2",
            title: "CPU Scheduling Algorithms: FCFS, SJF, Round Robin & Priority",
            type: "cheatsheet",
            pages: 8,
            uploadedDate: "24 Oct 2026",
            faculty: "Dr. Bose",
            summary: "Formulas and Gantt chart calculations for Turnaround Time (TAT) and Waiting Time (WT). Convoy effect in FCFS and starvation in priority scheduling.",
            keyTakeaways: ["Turnaround Time = Completion Time - Arrival Time.", "Waiting Time = Turnaround Time - Burst Time.", "SJF gives minimum average waiting time for given set of processes."],
            examQuestions: [{ question: "Compare Preemptive SJF (SRTF) and Round Robin scheduling.", marks: 5, answer: "SRTF prioritizes shortest remaining burst, minimizing average waiting time but risking starvation for long jobs. RR gives time slice quantum to all processes, preventing starvation." }],
          },
        ],
      },
      {
        unitNumber: 3,
        title: "Process Synchronization & Classical Deadlocks",
        status: "in-progress",
        weightage: "20 Marks",
        notes: [
          {
            id: "n-os-3",
            title: "Critical Section Problem, Semaphores & Dining Philosophers",
            type: "slides",
            pages: 38,
            uploadedDate: "06 Nov 2026",
            faculty: "Dr. Bose",
            summary: "Peterson's solution, counting vs binary semaphores, wait()/signal() atomic primitives, and Banker's algorithm for deadlock avoidance.",
            keyTakeaways: ["Three requirements: Mutual Exclusion, Progress, and Bounded Waiting.", "Deadlock necessary conditions: Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait."],
            examQuestions: [{ question: "State Peterson's algorithm for 2-process synchronization and prove mutual exclusion.", marks: 5, answer: "Peterson uses flag[2] array and turn variable. Process i sets flag[i]=true, turn=j, and loops while flag[j] and turn==j." }],
          },
        ],
      },
      {
        unitNumber: 4,
        title: "Memory Management & Paging",
        status: "upcoming",
        weightage: "15 Marks",
        notes: [
          {
            id: "n-os-4",
            title: "Virtual Memory, Paging, TLB & Page Replacement Algorithms",
            type: "slides",
            pages: 34,
            uploadedDate: "11 Nov 2026",
            faculty: "Dr. Bose",
            summary: "Logical to physical address translation, Page tables, Translation Lookaside Buffer (TLB), FIFO, LRU, and Optimal replacement.",
            keyTakeaways: ["Effective Memory Access Time (EMAT) = Hit_ratio * (TLB + Mem) + (1 - Hit_ratio) * (TLB + 2*Mem).", "Belady's anomaly occurs in FIFO page replacement."],
            examQuestions: [{ question: "Calculate EMAT given TLB hit ratio 90%, TLB access 20ns, memory access 100ns.", marks: 5, answer: "EMAT = 0.90*(20 + 100) + 0.10*(20 + 2*100) = 0.90*120 + 0.10*220 = 108 + 22 = 130 ns." }],
          },
        ],
      },
    ],
  },
  {
    id: "cs503",
    code: "CS503",
    name: "Computer Networks",
    faculty: "Prof. Suman Dasgupta",
    totalUnits: 3,
    completedUnits: 2,
    totalNotes: 8,
    examDate: "03 Dec 2026",
    examCountdownDays: 18,
    accentColor: "border-sky-500/40 text-sky-400 bg-sky-500/10",
    topics: ["OSI vs TCP/IP Layers", "Sliding Window Protocols (Go-Back-N / SR)", "IPv4 Subnetting & CIDR", "Routing (Dijkstra / Bellman-Ford)"],
    units: [
      {
        unitNumber: 1,
        title: "Layered Architecture & Physical/Data Link Transmission",
        status: "completed",
        weightage: "15 Marks",
        notes: [
          {
            id: "n-cn-1",
            title: "OSI 7 Layers vs TCP/IP Model Functions",
            type: "handout",
            pages: 18,
            uploadedDate: "08 Oct 2026",
            faculty: "Prof. Dasgupta",
            summary: "Roles of Physical, Data Link, Network, Transport, Session, Presentation, Application layers. Encapsulation and PDU names.",
            keyTakeaways: ["Transport layer PDU = Segment, Network = Packet, Data Link = Frame, Physical = Bit.", "TCP provides reliable, byte-stream connection; UDP is connectionless datagram."],
            examQuestions: [{ question: "Differentiate between OSI and TCP/IP reference models.", marks: 5, answer: "OSI has 7 layers and clearly distinguishes services, interfaces, and protocols. TCP/IP has 4 layers, was built around actual protocols, and combines presentation/session into application." }],
          },
        ],
      },
      {
        unitNumber: 2,
        title: "Sliding Window Protocols & Flow Control",
        status: "completed",
        weightage: "18 Marks",
        notes: [
          {
            id: "n-cn-2",
            title: "Stop-and-Wait, Go-Back-N & Selective Repeat Protocol Analysis",
            type: "cheatsheet",
            pages: 10,
            uploadedDate: "25 Oct 2026",
            faculty: "Prof. Dasgupta",
            summary: "Formulas for efficiency (η = N / (1 + 2a)), window sizes (GBN: Ws = 2^k - 1, Wr = 1; SR: Ws = Wr = 2^(k-1)), and sequence number bits.",
            keyTakeaways: ["a = T_prop / T_trans.", "In GBN, receiver window is always 1, out-of-order packets discarded.", "In SR, receiver window equals sender window, out-of-order packets buffered."],
            examQuestions: [{ question: "If bandwidth is 1 Gbps, 1-way delay is 10ms, packet size 1000 bytes, find minimum window size for 100% efficiency.", marks: 5, answer: "T_trans = (1000 * 8) / 10^9 = 8 microseconds. T_prop = 10ms = 10,000 microseconds. a = 10000 / 8 = 1250. Min window N = 1 + 2a = 1 + 2500 = 2501 packets." }],
          },
        ],
      },
      {
        unitNumber: 3,
        title: "Network Layer: IPv4, Subnetting & Routing Protocols",
        status: "in-progress",
        weightage: "20 Marks",
        notes: [
          {
            id: "n-cn-3",
            title: "CIDR, Subnet Masking Calculations & Distance Vector Routing",
            type: "slides",
            pages: 30,
            uploadedDate: "08 Nov 2026",
            faculty: "Prof. Dasgupta",
            summary: "IP address classes, CIDR prefix notation (/24, /27), subnet address, broadcast address, Count-to-Infinity problem, and Link State vs Distance Vector.",
            keyTakeaways: ["Number of hosts per subnet = 2^(32 - prefix) - 2.", "Dijkstra algorithm computes shortest path using global link states (OSPF)."],
            examQuestions: [{ question: "A network has IP block 200.10.20.0/24. Subnet it into 4 equal subnets. State subnet masks and host ranges.", marks: 5, answer: "Need 4 subnets -> borrow 2 bits -> prefix becomes /26 (mask 255.255.255.192). Each subnet has 64 IPs (62 usable hosts): 1) .0 to .63, 2) .64 to .127, 3) .128 to .191, 4) .192 to .255." }],
          },
        ],
      },
    ],
  },
  {
    id: "cs504",
    code: "CS504",
    name: "Artificial Intelligence & Machine Learning",
    faculty: "Dr. Gour Sundar Mitra Thakur",
    totalUnits: 3,
    completedUnits: 1,
    totalNotes: 9,
    examDate: "07 Dec 2026",
    examCountdownDays: 22,
    accentColor: "border-amber-500/40 text-amber-400 bg-amber-500/10",
    topics: ["Uninformed & Informed Search (A*)", "Game Playing (Minimax & Alpha-Beta)", "Knowledge Representation & First Order Logic", "Supervised Learning & Decision Trees"],
    units: [
      {
        unitNumber: 1,
        title: "Search Algorithms & Heuristics",
        status: "completed",
        weightage: "18 Marks",
        notes: [
          {
            id: "n-ai-1",
            title: "A* Search, Admissibility, Consistency & 8-Puzzle",
            type: "slides",
            pages: 26,
            uploadedDate: "15 Oct 2026",
            faculty: "Dr. Mitra Thakur",
            summary: "f(n) = g(n) + h(n). Admissible heuristics never overestimate the cost to reach the goal. Proof of A* optimality.",
            keyTakeaways: ["A* is optimal and complete if h(n) is admissible (tree search) or consistent (graph search).", "Manhattan distance dominates misplaced tiles for 8-puzzle."],
            examQuestions: [{ question: "Prove that A* search using tree search is optimal if heuristic h(n) is admissible.", marks: 5, answer: "Suppose sub-optimal goal G2 is chosen before optimal goal G1. Since h(G2)=0, f(G2)=g(G2)>g(G1). Since h is admissible, for some node n on optimal path to G1, f(n) <= g(G1) < f(G2). Thus n is expanded before G2." }],
          },
        ],
      },
      {
        unitNumber: 2,
        title: "Adversarial Search & Logic Representation",
        status: "in-progress",
        weightage: "18 Marks",
        notes: [
          {
            id: "n-ai-2",
            title: "Minimax Algorithm & Alpha-Beta Pruning Rules",
            type: "cheatsheet",
            pages: 12,
            uploadedDate: "02 Nov 2026",
            faculty: "Dr. Mitra Thakur",
            summary: "Zero-sum two-player games. Alpha (highest value choice for MAX) and Beta (lowest value choice for MIN). Pruning condition: α >= β.",
            keyTakeaways: ["Alpha-Beta pruning yields identical decisions to Minimax, with best case time complexity O(b^(d/2)).", "Move ordering drastically impacts the number of pruned branches."],
            examQuestions: [{ question: "Trace Alpha-Beta pruning on a game tree of depth 3 with branching factor 2.", marks: 5, answer: "Initialize α = -∞, β = +∞ at root. Evaluate left child to update α. At right child, if value <= α, prune remaining subtree." }],
          },
        ],
      },
      {
        unitNumber: 3,
        title: "Machine Learning Foundations",
        status: "upcoming",
        weightage: "15 Marks",
        notes: [
          {
            id: "n-ai-3",
            title: "Decision Trees (ID3), Entropy & Information Gain",
            type: "slides",
            pages: 24,
            uploadedDate: "10 Nov 2026",
            faculty: "Dr. Mitra Thakur",
            summary: "Shannon entropy formula: H(S) = -∑ p_i log2(p_i). Information Gain = Entropy(Parent) - Weighted Average Entropy(Children).",
            keyTakeaways: ["ID3 selects attribute with highest Information Gain at each node split.", "Overfitting countered by post-pruning."],
            examQuestions: [{ question: "Calculate Entropy for a target variable with 9 positive and 5 negative examples.", marks: 5, answer: "p+ = 9/14, p- = 5/14. H(S) = -(9/14)*log2(9/14) - (5/14)*log2(5/14) = 0.940 bits." }],
          },
        ],
      },
    ],
  },
];

// ==========================================
// MAIN COMPONENT
// ==========================================

export default function StudyCornerPage() {
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeNoteTab, setActiveNoteTab] = useState<"summary" | "exam" | "ai">("summary");
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);

  // AI Chat State inside note
  const [aiQuery, setAiQuery] = useState("");
  const [aiAnswers, setAiAnswers] = useState<{ query: string; reply: string }[]>([]);
  const [isAiLoading, setIsAiLoading] = useState(false);

  // Active Subject details
  const currentSubject = SUBJECTS.find((s) => s.id === selectedSubjectId);

  // Flattened notes for current subject
  const currentSubjectNotes: { note: NoteItem; unitNumber: number; unitTitle: string }[] =
    currentSubject
      ? currentSubject.units.flatMap((u) =>
          u.notes.map((n) => ({ note: n, unitNumber: u.unitNumber, unitTitle: u.title }))
        )
      : [];

  // Active selected note
  const activeNote =
    currentSubjectNotes.find((item) => item.note.id === selectedNoteId)?.note ||
    currentSubjectNotes[0]?.note;

  // Filter subjects for the main directory
  const filteredSubjects = SUBJECTS.filter(
    (s) =>
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.topics.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleOpenSubject = (subjectId: string) => {
    setSelectedSubjectId(subjectId);
    const sub = SUBJECTS.find((s) => s.id === subjectId);
    if (sub && sub.units[0]?.notes[0]) {
      setSelectedNoteId(sub.units[0].notes[0].id);
    }
    setActiveNoteTab("summary");
  };

  const handleSendAiDoubt = (presetText?: string) => {
    const text = presetText || aiQuery;
    if (!text.trim()) return;

    setIsAiLoading(true);
    setAiQuery("");

    setTimeout(() => {
      let reply = `Here is the concise explanation from the course repository:\n\n• In ${currentSubject?.code} (${activeNote?.title}), this concept directly relates to MAKAUT exam standards.\n• Key Exam Tip: Always draw the formal diagram or truth table first to secure full marks.\n• Reference: ${activeNote?.summary}`;

      if (text.toLowerCase().includes("analogy") || text.toLowerCase().includes("eli5")) {
        reply = `💡 Real-World Analogy:\nThink of this like a busy airport luggage carousel: if every passenger grabbed bags without looking at baggage tags, you'd get chaos (concurrency anomalies). The protocol ensures everyone checks out their tagged bag in an orderly queue.`;
      } else if (text.toLowerCase().includes("5 mark") || text.toLowerCase().includes("exam")) {
        reply = `🎯 To score full 5/5 on this in the BCREC End-Sem:\n1. State the exact formal definition (1 Mark)\n2. Write the 2 necessary mathematical conditions (2 Marks)\n3. Give one counter-example demonstrating the violation (2 Marks)`;
      }

      setAiAnswers((prev) => [...prev, { query: text, reply }]);
      setIsAiLoading(false);
    }, 450);
  };

  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* ======================================================== */}
        {/* VIEW 1: SUBJECT DIRECTORY (When no subject is opened)    */}
        {/* ======================================================== */}
        {!selectedSubjectId && (
          <div className="space-y-6">
            {/* Header Banner */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2.5">
                  <h1 className="text-xl font-bold text-white tracking-tight">Study Corner</h1>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-medium">
                    Semester 5 Repository
                  </span>
                </div>
                <p className="text-xs text-[#8A8F98] mt-1">
                  BCREC Computer Science & Engineering · All enrolled courses, unit-by-unit lecture notes, formula sheets & PYQs
                </p>
              </div>

              {/* Search Bar */}
              <div className="relative w-full md:w-72">
                <Search className="w-3.5 h-3.5 text-[#8A8F98] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Search subjects, topics, or notes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-[#121316] border border-white/[0.08] rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-[#6E7480] outline-none focus:border-[#5E6AD2] transition-colors"
                />
              </div>
            </div>

            {/* Critical Exam Notice Strip */}
            <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/25 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span className="w-2 h-2 rounded-full bg-rose-400 animate-pulse" />
                <span className="text-xs font-semibold text-rose-300">
                  Upcoming Exam: CS501 Database Management Systems starts in 8 Days (23 Nov 2026)
                </span>
              </div>
              <button
                onClick={() => handleOpenSubject("cs501")}
                className="text-xs text-rose-300 hover:text-white font-medium flex items-center gap-1 shrink-0 underline underline-offset-2"
              >
                Open CS501 Notes & PYQs <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            {/* Enrolled Subjects Grid */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-[#5E6AD2]" /> Enrolled Courses · Click a course to open notes
                </span>
                <span className="text-xs font-mono text-[#8A8F98]">4 Total Subjects</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredSubjects.map((sub) => {
                  const progressPct = Math.round((sub.completedUnits / sub.totalUnits) * 100);

                  return (
                    <Card
                      key={sub.id}
                      onClick={() => handleOpenSubject(sub.id)}
                      className="p-5 cursor-pointer bg-[#0D0E10] border-white/[0.08] hover:border-white/[0.20] hover:bg-[#121316] transition-all group relative overflow-hidden flex flex-col justify-between"
                    >
                      <div className="space-y-3">
                        {/* Top row: Code + Exam Countdown */}
                        <div className="flex items-center justify-between">
                          <span
                            className={`text-[11px] font-mono px-2 py-0.5 rounded border font-semibold ${sub.accentColor}`}
                          >
                            {sub.code}
                          </span>
                          <span className="text-[11px] font-mono text-[#8A8F98] flex items-center gap-1">
                            <Clock className="w-3 h-3 text-amber-400" />
                            Exam in {sub.examCountdownDays}d ({sub.examDate})
                          </span>
                        </div>

                        {/* Subject Title & Faculty */}
                        <div>
                          <h2 className="text-base font-bold text-white group-hover:text-[#5E6AD2] transition-colors">
                            {sub.name}
                          </h2>
                          <p className="text-xs text-[#8A8F98] mt-0.5">Faculty Lead: {sub.faculty}</p>
                        </div>

                        {/* Key Topics Tags */}
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {sub.topics.map((topic, tIdx) => (
                            <span
                              key={tIdx}
                              className="text-[10px] px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] text-[#9DA3AE]"
                            >
                              {topic}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Bottom Footer: Stats + Progress */}
                      <div className="pt-4 mt-4 border-t border-white/[0.06] space-y-2">
                        <div className="flex items-center justify-between text-xs text-[#8A8F98]">
                          <span>
                            {sub.totalUnits} Units · <span className="text-white font-medium">{sub.totalNotes} Note Files</span>
                          </span>
                          <span className="font-mono text-white font-medium">{progressPct}% Covered</span>
                        </div>

                        {/* Progress Bar */}
                        <div className="w-full h-1 bg-white/[0.08] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#5E6AD2] rounded-full transition-all"
                            style={{ width: `${progressPct}%` }}
                          />
                        </div>

                        <div className="flex items-center justify-between pt-1">
                          <span className="text-[11px] text-[#8A8F98]">
                            Unit {sub.completedUnits + 1} In Progress
                          </span>
                          <span className="text-xs font-semibold text-[#5E6AD2] group-hover:translate-x-0.5 transition-transform flex items-center gap-1">
                            Open Notes Vault <ChevronRight className="w-3 h-3" />
                          </span>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>

            {/* Quick Study Tools Showcase */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-white">
                  <FileText className="w-4 h-4 text-[#5E6AD2]" /> 1-Page Cheat Sheets
                </div>
                <p className="text-[11px] text-[#8A8F98] leading-relaxed">
                  High-yield formulas and comparison tables designed to review right before walking into the examination hall.
                </p>
              </Card>

              <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-white">
                  <Award className="w-4 h-4 text-amber-400" /> BCREC Solved PYQs
                </div>
                <p className="text-[11px] text-[#8A8F98] leading-relaxed">
                  Past 3 years autonomous question papers with model answers broken down by 5-mark and 10-mark structures.
                </p>
              </Card>

              <Card className="p-4 bg-[#0D0E10] border-white/[0.08] space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-white">
                  <Sparkles className="w-4 h-4 text-indigo-400" /> Grounded AI Tutor
                </div>
                <p className="text-[11px] text-[#8A8F98] leading-relaxed">
                  Ask doubts directly on your professor's slides with zero hallucinations. Everything cites exact syllabus pages.
                </p>
              </Card>
            </div>
          </div>
        )}

        {/* ======================================================== */}
        {/* VIEW 2: SUBJECT NOTES VAULT (When a subject is selected) */}
        {/* ======================================================== */}
        {currentSubject && (
          <div className="space-y-5">
            {/* Top Navigation & Breadcrumbs */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSelectedSubjectId(null)}
                  className="p-1.5 rounded-lg border border-white/[0.08] bg-[#121316] text-[#8A8F98] hover:text-white hover:border-white/[0.2] transition-colors flex items-center gap-1 text-xs"
                >
                  <ChevronLeft className="w-4 h-4" /> All Subjects
                </button>
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded border font-semibold ${currentSubject.accentColor}`}
                    >
                      {currentSubject.code}
                    </span>
                    <h1 className="text-base font-bold text-white">{currentSubject.name}</h1>
                  </div>
                  <p className="text-xs text-[#8A8F98] mt-0.5">
                    Faculty: {currentSubject.faculty} · ESE Exam on {currentSubject.examDate} (
                    <span className="text-amber-400 font-semibold">{currentSubject.examCountdownDays} Days</span>)
                  </p>
                </div>
              </div>

              {/* Subject Switcher pills */}
              <div className="flex items-center gap-1.5 bg-[#121316] p-1 rounded-lg border border-white/[0.08]">
                {SUBJECTS.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => handleOpenSubject(s.id)}
                    className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors ${
                      s.id === currentSubject.id
                        ? "bg-[#1C1D22] text-white border border-white/[0.12]"
                        : "text-[#8A8F98] hover:text-white"
                    }`}
                  >
                    {s.code}
                  </button>
                ))}
              </div>
            </div>

            {/* 2-Column Deep Note Workspace */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: Units & Notes Index (5 Cols) */}
              <div className="lg:col-span-5 space-y-4">
                <div className="flex items-center justify-between text-xs text-[#8A8F98]">
                  <span className="font-semibold uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-[#5E6AD2]" /> Syllabus Units & Notes
                  </span>
                  <span>{currentSubject.totalNotes} Files Available</span>
                </div>

                <div className="space-y-3">
                  {currentSubject.units.map((unit) => (
                    <div
                      key={unit.unitNumber}
                      className="rounded-lg bg-[#0D0E10] border border-white/[0.08] overflow-hidden"
                    >
                      {/* Unit Header */}
                      <div className="p-3 bg-[#121316] border-b border-white/[0.06] flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-mono font-bold text-[#5E6AD2]">
                            U{unit.unitNumber}
                          </span>
                          <span className="text-xs font-semibold text-white truncate">
                            {unit.title}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-[10px] font-mono text-[#8A8F98]">
                            {unit.weightage}
                          </span>
                          {unit.status === "completed" && (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          )}
                          {unit.status === "in-progress" && (
                            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                          )}
                        </div>
                      </div>

                      {/* Notes List under Unit */}
                      <div className="divide-y divide-white/[0.04]">
                        {unit.notes.map((note) => {
                          const isSelected = activeNote?.id === note.id;

                          return (
                            <div
                              key={note.id}
                              onClick={() => {
                                setSelectedNoteId(note.id);
                                setActiveNoteTab("summary");
                              }}
                              className={`p-3 cursor-pointer transition-all flex items-start justify-between gap-3 ${
                                isSelected
                                  ? "bg-[#1C1D22] border-l-2 border-[#5E6AD2]"
                                  : "hover:bg-white/[0.02]"
                              }`}
                            >
                              <div className="flex items-start gap-2.5 min-w-0">
                                <FileText
                                  className={`w-4 h-4 mt-0.5 shrink-0 ${
                                    isSelected ? "text-[#5E6AD2]" : "text-[#8A8F98]"
                                  }`}
                                />
                                <div className="min-w-0">
                                  <p
                                    className={`text-xs font-medium truncate ${
                                      isSelected ? "text-white" : "text-[#ECEEF0]"
                                    }`}
                                  >
                                    {note.title}
                                  </p>
                                  <div className="flex items-center gap-2 text-[10px] text-[#8A8F98] mt-0.5">
                                    <span
                                      className={`px-1.5 py-0.2 rounded font-mono uppercase font-semibold ${
                                        note.type === "slides"
                                          ? "bg-indigo-500/15 text-indigo-300"
                                          : note.type === "cheatsheet"
                                          ? "bg-amber-500/15 text-amber-300"
                                          : note.type === "pyq"
                                          ? "bg-emerald-500/15 text-emerald-300"
                                          : "bg-white/[0.06] text-[#9DA3AE]"
                                      }`}
                                    >
                                      {note.type}
                                    </span>
                                    <span>{note.pages} Pages</span>
                                    <span>· {note.uploadedDate}</span>
                                  </div>
                                </div>
                              </div>
                              <ChevronRight
                                className={`w-3.5 h-3.5 shrink-0 mt-1 transition-transform ${
                                  isSelected ? "text-[#5E6AD2] translate-x-0.5" : "text-[#6E7480]"
                                }`}
                              />
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Column: Note Reader & Study Workspace (7 Cols) */}
              <div className="lg:col-span-7 space-y-4">
                {activeNote ? (
                  <Card className="p-5 bg-[#0D0E10] border-white/[0.08] space-y-4 min-h-[560px] flex flex-col justify-between">
                    <div>
                      {/* Active Note Header */}
                      <div className="pb-3 border-b border-white/[0.06] flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold uppercase ${
                                activeNote.type === "slides"
                                  ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                                  : activeNote.type === "cheatsheet"
                                  ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                                  : "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                              }`}
                            >
                              {activeNote.type}
                            </span>
                            <span className="text-xs text-[#8A8F98] font-mono">
                              {activeNote.pages} Pages · By {activeNote.faculty}
                            </span>
                          </div>
                          <h2 className="text-base font-bold text-white mt-1.5 leading-snug">
                            {activeNote.title}
                          </h2>
                        </div>

                        {/* Top action buttons */}
                        <div className="flex items-center gap-2 shrink-0">
                          <Button size="sm" variant="secondary" icon={<Download className="w-3 h-3" />}>
                            Save PDF
                          </Button>
                        </div>
                      </div>

                      {/* Workspace Tabs */}
                      <div className="flex items-center gap-1.5 pt-3 pb-2">
                        <button
                          onClick={() => setActiveNoteTab("summary")}
                          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                            activeNoteTab === "summary"
                              ? "bg-[#1C1D22] text-white border border-white/[0.12]"
                              : "text-[#8A8F98] hover:text-white"
                          }`}
                        >
                          <BookOpen className="w-3.5 h-3.5 text-[#5E6AD2]" /> Core Takeaways
                        </button>
                        <button
                          onClick={() => setActiveNoteTab("exam")}
                          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                            activeNoteTab === "exam"
                              ? "bg-[#1C1D22] text-white border border-white/[0.12]"
                              : "text-[#8A8F98] hover:text-white"
                          }`}
                        >
                          <Award className="w-3.5 h-3.5 text-amber-400" /> 5-Mark Exam Answers ({activeNote.examQuestions.length})
                        </button>
                        <button
                          onClick={() => setActiveNoteTab("ai")}
                          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                            activeNoteTab === "ai"
                              ? "bg-[#1C1D22] text-white border border-white/[0.12]"
                              : "text-[#8A8F98] hover:text-white"
                          }`}
                        >
                          <Sparkles className="w-3.5 h-3.5 text-indigo-400" /> Ask Grounded AI
                        </button>
                      </div>

                      {/* TAB 1: SUMMARY & TAKEAWAYS */}
                      {activeNoteTab === "summary" && (
                        <div className="space-y-4 pt-2">
                          <div className="p-3.5 rounded-lg bg-[#121316] border border-white/[0.06] space-y-1.5">
                            <span className="text-[11px] font-semibold text-[#8A8F98] uppercase tracking-wider block">
                              Executive Concept Overview
                            </span>
                            <p className="text-xs text-[#ECEEF0] leading-relaxed">
                              {activeNote.summary}
                            </p>
                          </div>

                          <div className="space-y-2">
                            <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                              <FileCheck className="w-4 h-4 text-emerald-400" /> Must-Remember Key Formulas & Rules:
                            </span>

                            <div className="space-y-2">
                              {activeNote.keyTakeaways.map((takeaway, idx) => (
                                <div
                                  key={idx}
                                  className="p-3 rounded-lg bg-[#121316] border border-white/[0.04] flex items-start gap-2.5 text-xs text-[#ECEEF0] leading-relaxed"
                                >
                                  <span className="text-xs font-mono font-bold text-[#5E6AD2] shrink-0 mt-0.5">
                                    0{idx + 1}.
                                  </span>
                                  <span>{takeaway}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* TAB 2: EXAM ANSWERS */}
                      {activeNoteTab === "exam" && (
                        <div className="space-y-3 pt-2">
                          <span className="text-xs font-semibold text-[#8A8F98] uppercase tracking-wider block">
                            Model Answers for BCREC Semester Papers:
                          </span>

                          <div className="space-y-3">
                            {activeNote.examQuestions.map((eq, qIdx) => (
                              <div
                                key={qIdx}
                                className="p-3.5 rounded-lg bg-[#121316] border border-white/[0.06] space-y-2"
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <div className="flex items-start gap-2">
                                    <span className="text-xs font-mono font-bold text-amber-400 mt-0.5">
                                      Q{qIdx + 1}.
                                    </span>
                                    <p className="text-xs font-semibold text-white leading-snug">
                                      {eq.question}
                                    </p>
                                  </div>
                                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 shrink-0">
                                    {eq.marks} Marks
                                  </span>
                                </div>

                                <div className="p-3 rounded bg-[#0D0E10] border border-white/[0.04] text-xs text-[#ECEEF0] leading-relaxed whitespace-pre-line font-mono text-[11px]">
                                  {eq.answer}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* TAB 3: AI DOUBT COMPANION */}
                      {activeNoteTab === "ai" && (
                        <div className="space-y-3 pt-2">
                          {/* Preset Doubts */}
                          <div className="space-y-1.5">
                            <span className="text-[11px] font-semibold text-[#8A8F98] uppercase tracking-wider block">
                              Instant Explanations:
                            </span>
                            <div className="flex flex-wrap gap-2">
                              <button
                                onClick={() =>
                                  handleSendAiDoubt(
                                    `Explain the core concept in "${activeNote.title}" using a real-world analogy.`
                                  )
                                }
                                className="text-[11px] px-2.5 py-1 rounded bg-[#121316] border border-white/[0.08] hover:border-white/[0.2] text-[#ECEEF0] transition-colors"
                              >
                                💡 Explain with Real-World Analogy
                              </button>
                              <button
                                onClick={() =>
                                  handleSendAiDoubt(
                                    `What are the most repeated 5-mark exam questions from this note?`
                                  )
                                }
                                className="text-[11px] px-2.5 py-1 rounded bg-[#121316] border border-white/[0.08] hover:border-white/[0.2] text-[#ECEEF0] transition-colors"
                              >
                                🎯 Expected 5-Mark Questions
                              </button>
                            </div>
                          </div>

                          {/* Messages */}
                          <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
                            {aiAnswers.map((item, aIdx) => (
                              <div key={aIdx} className="space-y-1.5">
                                <div className="text-right">
                                  <span className="inline-block bg-[#1C1D22] text-xs text-white px-3 py-1.5 rounded-lg border border-white/[0.08]">
                                    {item.query}
                                  </span>
                                </div>
                                <div className="p-3 rounded-lg bg-[#121316] border border-white/[0.06] text-xs text-[#ECEEF0] whitespace-pre-line leading-relaxed">
                                  {item.reply}
                                </div>
                              </div>
                            ))}

                            {isAiLoading && (
                              <div className="p-2.5 text-xs text-[#8A8F98] italic flex items-center gap-2">
                                <Sparkles className="w-3.5 h-3.5 text-[#5E6AD2] animate-spin" />
                                Analyzing professor slides for exact citations...
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* AI Prompt Input Bar (only active in AI tab or bottom) */}
                    {activeNoteTab === "ai" && (
                      <div className="pt-3 border-t border-white/[0.06]">
                        <div className="flex items-center gap-2 bg-[#121316] border border-white/[0.1] rounded-lg p-2 focus-within:border-[#5E6AD2] transition-colors">
                          <input
                            type="text"
                            placeholder="Ask any doubt regarding this specific note..."
                            value={aiQuery}
                            onChange={(e) => setAiQuery(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSendAiDoubt()}
                            className="flex-1 bg-transparent text-xs text-white placeholder-[#6E7480] px-2 py-1 outline-none"
                          />
                          <Button
                            size="sm"
                            onClick={() => handleSendAiDoubt()}
                            disabled={!aiQuery.trim()}
                            icon={<Send className="w-3 h-3" />}
                          >
                            Ask
                          </Button>
                        </div>
                      </div>
                    )}
                  </Card>
                ) : (
                  <Card className="p-8 text-center bg-[#0D0E10] border-white/[0.08] space-y-2">
                    <BookOpen className="w-8 h-8 text-[#8A8F98] mx-auto" />
                    <p className="text-sm font-semibold text-white">Select a note from the left index</p>
                    <p className="text-xs text-[#8A8F98]">
                      Choose any lecture slide or formula sheet to read takeaways and 5-mark model answers.
                    </p>
                  </Card>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </StudentLayout>
  );
}
