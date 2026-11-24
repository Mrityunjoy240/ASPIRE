// apps/web/app/lib/types.ts
// TypeScript contract types for the Mother Application (Web).
// These mirror the FastAPI Pydantic schemas in app/api/schemas.py.
// Source of truth: contracts/openapi.json (DM-API01).

// --- Mentor Queue ---

export type CaseQueueItemResponse = {
  case_id: string;
  student_id: string;
  student_name: string;
  student_roll: string;
  urgency_band: string;     // URGENT | ATTENTION | MONITOR
  status: string;           // OPEN | IN_REVIEW | PLAN_PROPOSED | PENDING_APPROVAL | ...
  trigger_events: string[]; // Array of event-ID strings (e.g. ["LOW_ATTENDANCE"])
  opened_at: string;
  nearest_exam_days: number | null;
  days_since_last_action: number | null;
};

export type CaseQueueItem = CaseQueueItemResponse;

export type CaseApproveRequest = {
  mentor_notes: string | null;
  decision: 'APPROVED' | 'EDITED' | 'REJECTED';
};

export type CaseApproveResponse = {
  case_id: string;
  mentor_decision: 'APPROVED' | 'EDITED' | 'REJECTED';
  acted_at: string;
};

// --- Admin: Institution Management ---

export type InstitutionRules = {
  attendance_threshold: number | null;
  grade_threshold: number | null;
  ai_enabled: boolean | null;
  escalation_days: number | null;
};

export type Institution = {
  id: string;
  name: string;
  slug: string;        // unique identifier, e.g. "bcrec-durgapur"
  status: 'ACTIVE' | 'SUSPENDED';
  rules: InstitutionRules | null;
};
