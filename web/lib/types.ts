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

export type DocumentKind = "salary_slip" | "bank_statement" | "other";

/** One supporting document, already converted to text. */
export interface Document {
  name: string;
  kind: DocumentKind;
  text: string;
}

/** What the applicant typed into the form. Every number may be left out. */
export interface ApplicationForm {
  annual_income: number | null;
  loan_amount: number | null;
  annuity: number | null;
  goods_price: number | null;
  years_employed: number | null;
  ext_source_1: number | null;
  ext_source_2: number | null;
  ext_source_3: number | null;
}

/** The raw submission (ApplicationInput), stored in applications.input. */
export interface ApplicationInput {
  form: ApplicationForm;
  documents: Document[];
  replies: string[];
  corrections: Partial<Record<keyof ApplicantFields, number>>;
}

/** A row of the applications table. */
export interface Application {
  id: string;
  status: Status;
  input: ApplicationInput;
  fields: ApplicantFields | null;
  metrics: Metrics | null;
  agent_output: ReasonerOutput | null;
  /** Question for the applicant while status is needs_info; null otherwise. */
  human_question: string | null;
  final_decision: HumanDecision | null;
  decision_reason: string | null;
  decided_by: string | null;
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

// --- Request and response bodies, mirroring api/app/models/application.py and routes. ---

/** Body for POST /applications. Never carries protected attributes (hard rule 4). */
export interface CreateApplicationRequest {
  form: ApplicationForm;
  documents: Document[];
}

/** Returned with 202 by POST /applications and POST /applications/{id}/reply. */
export interface ApplicationAccepted {
  id: string;
  status: Status;
}

/** Body for POST /applications/{id}/reply. Corrected values win over extracted ones. */
export interface ReplyRequest {
  answer: string;
  corrections: Partial<Record<keyof ApplicantFields, number>>;
}

export type DecisionAction = "approve" | "reject" | "override";

/**
 * Body for POST /applications/{id}/decision.
 * approve/reject must agree with the agent; going against it is an override with final_decision.
 * A reason is required for reject and override (hard rule 6).
 */
export interface DecisionRequest {
  reviewer_id: string;
  action: DecisionAction;
  final_decision: HumanDecision | null;
  reason: string | null;
}
