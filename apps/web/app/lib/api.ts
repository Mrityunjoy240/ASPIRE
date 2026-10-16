// apps/web/app/lib/api.ts
// Typed ASPIRE Core API client (Mother Application → FastAPI gateway).
// Auth: Bearer token from localStorage (aspire_token) with
// NEXT_PUBLIC_ASPIRE_DEV_TOKEN as the developer fallback (lead-approved).
// Frontend never contains business logic — it only calls Core API contracts
// (AGENTS.md: clients must not duplicate core business logic).

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_STORAGE_KEY = "aspire_token";

export function getAuthToken(): string | null {
  if (typeof window !== "undefined") {
    const stored = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    if (stored) return stored;
  }
  return process.env.NEXT_PUBLIC_ASPIRE_DEV_TOKEN || null;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAuthToken();
  if (!token) {
    throw new ApiError(
      401,
      "Not authenticated: set NEXT_PUBLIC_ASPIRE_DEV_TOKEN or sign in (localStorage aspire_token)."
    );
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, `Cannot reach ASPIRE Core API at ${API_BASE}`);
  }

  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = typeof body?.detail === "string" ? `: ${body.detail}` : "";
    } catch {
      detail = "";
    }
    throw new ApiError(response.status, `Request failed (${response.status})${detail}`);
  }

  return (await response.json()) as T;
}

// --- Contract types (mirror contracts/openapi.json) ---

export interface CaseQueueItem {
  case_id: string;
  student_id: string;
  student_name: string;
  student_roll: string;
  urgency_band: string;
  status: string;
  trigger_events: string[];
  opened_at: string;
  nearest_exam_days: number | null;
  days_since_last_action: number | null;
}

export interface CaseApproveResponse {
  case_id: string;
  mentor_decision: "APPROVED" | "EDITED" | "REJECTED";
  acted_at: string;
}

// --- Endpoints ---

export function fetchCaseQueue(): Promise<CaseQueueItem[]> {
  return apiFetch<CaseQueueItem[]>("/api/v1/cases/queue");
}

export function approveCase(
  caseId: string,
  decision: CaseApproveResponse["mentor_decision"],
  mentorNotes?: string
): Promise<CaseApproveResponse> {
  return apiFetch<CaseApproveResponse>(`/api/v1/cases/${caseId}/approve`, {
    method: "POST",
    body: JSON.stringify({ decision, mentor_notes: mentorNotes ?? null }),
  });
}
