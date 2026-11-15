export interface ClassroomCourse {
  id: string;
  code: string;
  name: string;
  faculty: string;
  facultyAvatar: string;
  room: string;
  color: string;
  accentBorder: string;
  totalNotes: number;
  totalAssignments: number;
  pendingAssignment?: {
    title: string;
    dueDate: string;
    isUrgent: boolean;
  };
  announcementCount: number;
  examDate: string;
  examCountdown: number;
  description: string;
}

export const CLASSROOM_COURSES: ClassroomCourse[] = [
  {
    id: "cs501",
    code: "CS501",
    name: "Database Management Systems",
    faculty: "Prof. Raj Kumar Samanta",
    facultyAvatar: "RS",
    room: "Room 302",
    color: "from-indigo-900/60 via-indigo-950/40 to-[#0D0E10]",
    accentBorder: "border-indigo-500/30",
    totalNotes: 14,
    totalAssignments: 2,
    pendingAssignment: {
      title: "CA2: Normalization & Canonical Covers",
      dueDate: "Tonight 23:59",
      isUrgent: true,
    },
    announcementCount: 4,
    examDate: "23 Nov 2026",
    examCountdown: 8,
    description: "Relational database concepts, SQL algebra, 3NF/BCNF normalization, transaction ACID properties, and B+ tree indexing.",
  },
  {
    id: "cs502",
    code: "CS502",
    name: "Operating Systems",
    faculty: "Dr. Anirban Bose",
    facultyAvatar: "AB",
    room: "Room 304",
    color: "from-purple-900/60 via-purple-950/40 to-[#0D0E10]",
    accentBorder: "border-purple-500/30",
    totalNotes: 11,
    totalAssignments: 1,
    pendingAssignment: {
      title: "Assignment 2: Banker's Algorithm Implementation",
      dueDate: "18 Nov, 5:00 PM",
      isUrgent: false,
    },
    announcementCount: 2,
    examDate: "28 Nov 2026",
    examCountdown: 13,
    description: "Dual-mode hardware, process scheduling, synchronization semaphores, memory paging, and virtual memory.",
  },
  {
    id: "cs503",
    code: "CS503",
    name: "Computer Networks",
    faculty: "Prof. Suman Dasgupta",
    facultyAvatar: "SD",
    room: "Room 206",
    color: "from-sky-900/60 via-sky-950/40 to-[#0D0E10]",
    accentBorder: "border-sky-500/30",
    totalNotes: 8,
    totalAssignments: 1,
    pendingAssignment: {
      title: "Lab Task: Packet Tracer Subnetting Lab",
      dueDate: "20 Nov, 23:59",
      isUrgent: false,
    },
    announcementCount: 3,
    examDate: "03 Dec 2026",
    examCountdown: 18,
    description: "OSI 7-layer vs TCP/IP model, sliding window protocols, IPv4 CIDR subnetting, and routing protocols.",
  },
  {
    id: "cs504",
    code: "CS504",
    name: "Artificial Intelligence & ML",
    faculty: "Dr. Gour Sundar Mitra Thakur",
    facultyAvatar: "GM",
    room: "Room 308",
    color: "from-amber-900/60 via-amber-950/40 to-[#0D0E10]",
    accentBorder: "border-amber-500/30",
    totalNotes: 9,
    totalAssignments: 1,
    pendingAssignment: {
      title: "Mini-Project: A* 8-Puzzle Solver Submission",
      dueDate: "25 Nov, 23:59",
      isUrgent: false,
    },
    announcementCount: 1,
    examDate: "07 Dec 2026",
    examCountdown: 22,
    description: "Search algorithms, heuristic admissible functions, Alpha-Beta minimax pruning, and supervised decision tree induction.",
  },
];
