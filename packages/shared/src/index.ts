/**
 * Shared cross-app constants and display types.
 * No framework code. No business logic (Constitution: engines calculate,
 * frontend consumes the Mother System API).
 */

export const ASPIRE_APP_VERSION = "0.1.0";

/** Fact provenance labels surfaced on every academic figure in the UI. */
export type Provenance = "VERIFIED" | "DERIVED" | "PROPOSED";

export const PROVENANCE_LABELS: Readonly<Record<Provenance, string>> = {
  VERIFIED: "Verified record",
  DERIVED: "Engine calculation",
  PROPOSED: "AI suggestion",
};

/** Task priority levels. */
export type Priority = "critical" | "high" | "medium" | "low";

/** Task status values. */
export type TaskStatus = "pending" | "completed" | "snoozed";

/** A display-only helper for non-null strings. Not a rule engine. */
export function isNonEmpty(value: string): boolean {
  return value.trim().length > 0;
}
