// In-memory demo data, used only when Supabase or the API URL is not configured.
// Rows, events and request rules mirror api/app (pipeline.py, routes). The demo never extracts,
// computes metrics or recommends: new cases fall back to `refer` for a human, as hard rule 7 does.

import type { DataSource } from "./data";
import { contradictsAgent } from "./decision";
import { ApiError } from "./errors";
import {
  REQUIRED_FIELDS,
  type ApplicantFields,
  type Application,
  type ApplicationForm,
  type AuditEvent,
  type Document,
  type HumanDecision,
  type ReasonerOutput,
  type Status,
} from "./types";

const MINUTE = 60_000;
const ANALYZE_DELAY_MS = 1200;
const ROUTE_DELAY_MS = 2400;
const HTTP_CONFLICT = 409;
const HTTP_NOT_FOUND = 404;
const HTTP_UNPROCESSABLE = 422;

let nextEventId = 1;
const applications = new Map<string, Application>();
const events = new Map<string, AuditEvent[]>();
const listeners = new Set<() => void>();

const EMPTY_FORM: ApplicationForm = {
  annual_income: null,
  loan_amount: null,
  annuity: null,
  goods_price: null,
  years_employed: null,
  ext_source_1: null,
  ext_source_2: null,
  ext_source_3: null,
};

function fieldsFrom(form: ApplicationForm, documentIncome: number | null = null): ApplicantFields {
  return { ...form, document_income: documentIncome };
}

function iso(msAgo: number): string {
  return new Date(Date.now() - msAgo).toISOString();
}

function log(
  appId: string,
  actor: string,
  event_type: string,
  payload: Record<string, unknown> = {},
  at = new Date().toISOString(),
): void {
  const list = events.get(appId) ?? [];
  list.push({ id: nextEventId++, application_id: appId, actor, event_type, payload, created_at: at });
  events.set(appId, list);
}

function notify(): void {
  listeners.forEach((fn) => fn());
}

function setStatus(app: Application, status: Status, actor = "system", columns: Partial<Application> = {}): void {
  log(app.id, actor, "status_changed", { from: app.status, to: status });
  Object.assign(app, columns, { status, updated_at: new Date().toISOString() });
  notify();
}

interface Seed {
  id: string;
  minutesAgo: number;
  status: Status;
  form: Partial<ApplicationForm>;
  documentIncome?: number;
  metrics: Application["metrics"];
  output: ReasonerOutput | null;
  question?: string;
  decision?: { final: HumanDecision; reason: string; override: boolean };
}

const SEEDS: Seed[] = [
  {
    id: "a1f3c2d4-0001-4c1a-9f10-5a1b2c3d4e01",
    minutesAgo: 42,
    status: "auto_cleared",
    form: { annual_income: 150_000, loan_amount: 450_000, annuity: 15_000, goods_price: 400_000, years_employed: 6, ext_source_1: 0.72, ext_source_2: 0.68, ext_source_3: 0.7 },
    documentIncome: 150_000,
    metrics: { loan_to_income: 3, payment_to_income: 1.2, income_mismatch_pct: 0 },
    output: {
      recommendation: "approve",
      confidence: 0.9,
      reasons: ["payment_to_income 1.20 is below the 2.77 refer limit", "loan_to_income 3.00 is below the 5.23 refer limit", "average external score 0.70 is healthy"],
      needs_human: false,
      human_question: null,
    },
  },
  {
    id: "b2e4d3c5-0002-4d2b-8e21-6b2c3d4e5f02",
    minutesAgo: 31,
    status: "needs_info",
    form: { annual_income: 150_000, loan_amount: 300_000, annuity: 12_000, goods_price: 280_000, years_employed: 3.2, ext_source_1: 0.6, ext_source_2: 0.65, ext_source_3: 0.62 },
    documentIncome: 100_000,
    metrics: { loan_to_income: 2, payment_to_income: 0.96, income_mismatch_pct: 0.5 },
    output: {
      recommendation: "approve",
      confidence: 0.9,
      reasons: ["payment_to_income 0.96 is low", "loan_to_income 2.00 is low", "average external score 0.62 is healthy"],
      needs_human: false,
      human_question: null,
    },
    question: "The income on your form (150,000.00) differs from the income on your document (100,000.00). Which figure is correct?",
  },
  {
    id: "c3f5e4d6-0003-4e3c-9d32-7c3d4e5f6a03",
    minutesAgo: 24,
    status: "pending_review",
    form: { annual_income: 120_000, loan_amount: 500_000, annuity: 30_000, goods_price: 450_000, years_employed: 1.1, ext_source_2: 0.42 },
    documentIncome: 118_000,
    metrics: { loan_to_income: 4.17, payment_to_income: 3, income_mismatch_pct: 0.017 },
    output: {
      recommendation: "refer",
      confidence: 0.6,
      reasons: ["payment_to_income 3.00 is above the 2.77 refer limit", "average external score 0.42 is in the refer band", "ext_source_1 and ext_source_3 are missing"],
      needs_human: true,
      human_question: "Is there a guarantor or additional income that offsets the high payment-to-income?",
    },
  },
  {
    id: "d4a6f5e7-0004-4f4d-8c43-8d4e5f6a7b04",
    minutesAgo: 17,
    status: "pending_review",
    form: { annual_income: 600_000, loan_amount: 1_500_000, annuity: 45_000, goods_price: 1_400_000, years_employed: 11, ext_source_1: 0.74, ext_source_2: 0.79, ext_source_3: 0.7 },
    documentIncome: 600_000,
    metrics: { loan_to_income: 2.5, payment_to_income: 0.9, income_mismatch_pct: 0 },
    output: {
      recommendation: "approve",
      confidence: 0.9,
      reasons: ["payment_to_income 0.90 is low", "loan_to_income 2.50 is below the refer limit", "average external score 0.74 is strong"],
      needs_human: false,
      human_question: null,
    },
  },
  {
    id: "e5b7a6f8-0005-4a5e-9b54-9e5f6a7b8c05",
    minutesAgo: 9,
    status: "needs_info",
    form: { annual_income: 200_000, loan_amount: 350_000, years_employed: 2 },
    metrics: null,
    output: null,
    question: "Please provide the following missing information: annuity, goods_price.",
  },
  {
    id: "f6c8b7a9-0006-4b6f-8a65-af6a7b8c9d06",
    minutesAgo: 5,
    status: "pending_review",
    form: { annual_income: 90_000, loan_amount: 600_000, annuity: 30_000, goods_price: 550_000, years_employed: 0.4, ext_source_2: 0.3 },
    documentIncome: 88_000,
    metrics: { loan_to_income: 6.67, payment_to_income: 4, income_mismatch_pct: 0.023 },
    output: {
      recommendation: "decline",
      confidence: 0.85,
      reasons: ["payment_to_income 4.00 is above the 3.65 decline limit", "average external score 0.30 is in the decline band"],
      needs_human: true,
      human_question: "Confirm decline: affordability fails on payment_to_income.",
    },
  },
  {
    id: "a7d9c8ba-0007-4c7a-9b76-b07b8c9d0e07",
    minutesAgo: 75,
    status: "decided",
    form: { annual_income: 160_000, loan_amount: 500_000, annuity: 50_000, goods_price: 480_000, years_employed: 4, ext_source_2: 0.52 },
    documentIncome: 158_000,
    metrics: { loan_to_income: 3.13, payment_to_income: 3.75, income_mismatch_pct: 0.013 },
    output: {
      recommendation: "decline",
      confidence: 0.85,
      reasons: ["payment_to_income 3.75 is above the 3.65 decline limit"],
      needs_human: true,
      human_question: "Is the payment affordable given the applicant's stable employment?",
    },
    decision: {
      final: "approve",
      override: true,
      reason: "Four years with the same employer and a matching bank statement; payment is affordable.",
    },
  },
];

const DEMO_REVIEWER = "officer.demo";

function seed(): void {
  for (const s of SEEDS) {
    const created = s.minutesAgo * MINUTE;
    const form = { ...EMPTY_FORM, ...s.form };
    const documents: Document[] =
      s.documentIncome != null
        ? [{ name: "bank_statement.txt", kind: "bank_statement", text: `Annual income: ${s.documentIncome.toLocaleString("en-US")}` }]
        : [];
    const app: Application = {
      id: s.id,
      status: s.status,
      input: { form, documents, replies: [], corrections: {} },
      fields: fieldsFrom(form, s.documentIncome ?? null),
      metrics: s.metrics,
      agent_output: s.output,
      human_question: s.status === "needs_info" ? (s.question ?? null) : null,
      final_decision: s.decision?.final ?? null,
      decision_reason: s.decision?.reason ?? null,
      decided_by: s.decision ? DEMO_REVIEWER : null,
      created_at: iso(created),
      updated_at: iso(created - 2 * MINUTE),
    };
    applications.set(app.id, app);
    log(app.id, "applicant", "application_submitted", {}, iso(created));
    log(app.id, "system", "status_changed", { from: "submitted", to: "analyzing" }, iso(created - 5_000));
    log(app.id, "system", "fields_extracted", {}, iso(created - 20_000));
    if (!s.output) {
      const missing = REQUIRED_FIELDS.filter((k) => form[k] == null);
      log(app.id, "system", "missing_fields", { missing }, iso(created - 21_000));
    } else {
      log(app.id, "system", "recommendation", { metrics: s.metrics, output: s.output }, iso(created - 40_000));
      const routed = s.status === "decided" ? "pending_review" : s.status;
      log(app.id, "system", "routed", { status: routed, human_question: s.question ?? null }, iso(created - 41_000));
    }
    const routedTo = s.status === "decided" ? "pending_review" : s.status;
    log(app.id, "system", "status_changed", { from: "analyzing", to: routedTo }, iso(created - 42_000));
    if (s.decision) {
      const at = iso(created - 20 * MINUTE);
      log(app.id, DEMO_REVIEWER, "reviewer_decision", {
        action: s.decision.override ? "override" : s.decision.final,
        final_decision: s.decision.final,
        reason: s.decision.reason,
      }, at);
      log(app.id, DEMO_REVIEWER, "status_changed", { from: "pending_review", to: "decided" }, at);
    }
  }
}

seed();

function fallbackOutput(): ReasonerOutput {
  return {
    recommendation: "refer",
    confidence: 0,
    reasons: ["Demo mode: the agent API is not connected, so this case is referred to a reviewer"],
    needs_human: true,
    human_question: "Please review this application manually.",
  };
}

function mustGet(id: string): Application {
  const app = applications.get(id);
  if (!app) throw new ApiError("application not found", HTTP_NOT_FOUND);
  return app;
}

/** Stand-in for one pipeline run: completeness check, then refer to a human. */
function runPipeline(app: Application): void {
  setTimeout(() => setStatus(app, "analyzing"), ANALYZE_DELAY_MS);
  setTimeout(() => {
    const fields = { ...fieldsFrom(app.input.form), ...app.input.corrections };
    log(app.id, "system", "fields_extracted", {});
    const missing = REQUIRED_FIELDS.filter((k) => fields[k] == null);
    if (missing.length) {
      log(app.id, "system", "missing_fields", { missing });
      setStatus(app, "needs_info", "system", {
        fields,
        human_question: `Please provide the following missing information: ${missing.join(", ")}.`,
      });
      return;
    }
    const output = fallbackOutput();
    log(app.id, "system", "recommendation", { metrics: null, output });
    log(app.id, "system", "routed", { status: "pending_review", human_question: null });
    setStatus(app, "pending_review", "system", { fields, agent_output: output, human_question: null });
  }, ROUTE_DELAY_MS);
}

export const demoSource: DataSource = {
  async listApplications() {
    return [...applications.values()]
      .map((a) => ({ ...a }))
      .sort((a, b) => b.created_at.localeCompare(a.created_at));
  },

  async getApplication(id) {
    const app = applications.get(id);
    return app ? { ...app } : null;
  },

  async listAuditEvents(id) {
    return [...(events.get(id) ?? [])];
  },

  subscribe(onChange) {
    listeners.add(onChange);
    return () => {
      listeners.delete(onChange);
    };
  },

  async createApplication(body) {
    const now = new Date().toISOString();
    const app: Application = {
      id: crypto.randomUUID(),
      status: "submitted",
      input: { form: body.form, documents: body.documents, replies: [], corrections: {} },
      fields: null,
      metrics: null,
      agent_output: null,
      human_question: null,
      final_decision: null,
      decision_reason: null,
      decided_by: null,
      created_at: now,
      updated_at: now,
    };
    applications.set(app.id, app);
    log(app.id, "applicant", "application_submitted");
    notify();
    runPipeline(app);
    return { id: app.id, status: app.status };
  },

  async reply(id, body) {
    const app = mustGet(id);
    if (app.status !== "needs_info") {
      throw new ApiError(`application is ${app.status}, not waiting for a reply`, HTTP_CONFLICT);
    }
    app.input = {
      ...app.input,
      replies: [...app.input.replies, body.answer],
      corrections: { ...app.input.corrections, ...body.corrections },
    };
    log(id, "applicant", "applicant_replied", { corrected_fields: Object.keys(body.corrections).sort() });
    notify();
    runPipeline(app);
    return { id: app.id, status: app.status };
  },

  async decide(id, body) {
    const app = mustGet(id);
    if (app.status !== "pending_review" && app.status !== "auto_cleared") {
      throw new ApiError(`cannot decide an application that is ${app.status}`, HTTP_CONFLICT);
    }
    if (body.action !== "approve" && !body.reason?.trim()) {
      throw new ApiError(`a reason is required for ${body.action}`, HTTP_UNPROCESSABLE);
    }
    const recommendation = app.agent_output?.recommendation;
    const final: HumanDecision = body.action === "override" && body.final_decision ? body.final_decision : body.action === "reject" ? "reject" : "approve";
    if (body.action !== "override" && contradictsAgent(final, recommendation)) {
      throw new ApiError(`${body.action} contradicts the agent's ${recommendation}; use override with a reason`, HTTP_CONFLICT);
    }
    log(id, body.reviewer_id, "reviewer_decision", { action: body.action, final_decision: final, reason: body.reason });
    setStatus(app, "decided", body.reviewer_id, {
      final_decision: final,
      decision_reason: body.reason,
      decided_by: body.reviewer_id,
    });
  },
};
