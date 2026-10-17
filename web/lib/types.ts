// Mirrors api/app/models/status.py, api/app/models/contract.py and db/schema.sql.
// If any of those change, change this file in the same PR.

export const STATUSES = [
  "submitted",
  "analyzing",
  "needs_info",
  "pending_review",
  "auto_cleared",
  "decided",
] as const;
export type Status = (typeof STATUSES)[number];

export const RECOMMENDATIONS = ["approve", "decline", "refer"] as const;
export type Recommendation = (typeof RECOMMENDATIONS)[number];

export type HumanDecision = "approve" | "reject";

export const REQUIRED_FIELDS = ["annual_income", "loan_amount", "annuity", "goods_price"] as const;

export interface ApplicantFields {
  annual_income: number | null;
  document_income: number | null;
  loan_amount: number | null;
  annuity: number | null;
  goods_price: number | null;
  years_employed: number | null;
  ext_source_1: number | null;
  ext_source_2: number | null;
  ext_source_3: number | null;
}

export interface Metrics {
  loan_to_income: number;
  payment_to_income: number;
  /** Fraction, not percent: 0.10 means 10%. */
  income_mismatch_pct: number | null;
}

export interface ReasonerOutput {
  recommendation: Recommendation;
  confidence: number;
  reasons: string[];
  needs_human: boolean;
  human_question: string | null;
}

/** A row of the applications table. */
export interface Application {
  id: string;
  status: Status;
  fields: ApplicantFields | null;
  metrics: Metrics | null;
  agent_output: ReasonerOutput | null;
  created_at: string;
  updated_at: string;
}

/** A row of the audit_log table. */
export interface AuditEvent {
  id: number;
  application_id: string;
  actor: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

// --- Request bodies. ASSUMED shapes: the API routes are not implemented yet. ---

/** Body for POST /applications. Never carries protected attributes (hard rule 4). */
export interface CreateApplicationRequest {
  annual_income: number | null;
  document_income: number | null;
  loan_amount: number | null;
  annuity: number | null;
  goods_price: number | null;
  years_employed: number | null;
}

export interface CreateApplicationResponse {
  id: string;
  status: Status;
}

/** Body for POST /applications/{id}/reply. */
export interface ReplyRequest {
  answer: string;
}

/**
 * Body for POST /applications/{id}/decision.
 * `override` is true when the reviewer's decision goes against the agent's recommendation.
 * A reason is required for reject and for override (hard rule 6).
 */
export interface DecisionRequest {
  decision: HumanDecision;
  override: boolean;
  reason: string | null;
}
