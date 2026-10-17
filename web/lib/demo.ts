// In-memory demo data, used only when Supabase or the API URL is not configured.
// Seeds mirror the five demo paths in the project plan. The demo never computes metrics or
// recommendations: new cases fall back to `refer` for a human, as hard rule 7 does.

import type { DataSource } from "./data";
import {
  REQUIRED_FIELDS,
  type ApplicantFields,
  type Application,
  type AuditEvent,
  type ReasonerOutput,
  type Status,
} from "./types";

const MINUTE = 60_000;
const ANALYZE_DELAY_MS = 1200;
const ROUTE_DELAY_MS = 2400;

let nextEventId = 1;
const applications = new Map<string, Application>();
const events = new Map<string, AuditEvent[]>();
const listeners = new Set<() => void>();

function emptyFields(): ApplicantFields {
  return {
    annual_income: null,
    document_income: null,
    loan_amount: null,
    annuity: null,
    goods_price: null,
    years_employed: null,
    ext_source_1: null,
    ext_source_2: null,
    ext_source_3: null,
  };
}

function iso(msAgo: number): string {
  return new Date(Date.now() - msAgo).toISOString();
}

function log(
  appId: string,
  actor: string,
  event_type: string,
  payload: Record<string, unknown>,
  at = new Date().toISOString(),
): void {
  const list = events.get(appId) ?? [];
  list.push({ id: nextEventId++, application_id: appId, actor, event_type, payload, created_at: at });
  events.set(appId, list);
}

function notify(): void {
  listeners.forEach((fn) => fn());
}

function setStatus(
  app: Application,
  status: Status,
  actor = "agent",
  extra: Record<string, unknown> = {},
): void {
  log(app.id, actor, "status_changed", {
    from: app.status,
    to: status,
    ...extra,
  });
  app.status = status;
  app.updated_at = new Date().toISOString();
  notify();
}

interface Seed {
  id: string;
  minutesAgo: number;
  status: Status;
  fields: Partial<ApplicantFields>;
  metrics: Application["metrics"];
  output: ReasonerOutput | null;
  question?: string;
  decision?: { decision: "approve" | "reject"; reason: string; override: boolean };
}

const SEEDS: Seed[] = [
  {
    id: "a1f3c2d4-0001-4c1a-9f10-5a1b2c3d4e01",
    minutesAgo: 42,
    status: "auto_cleared",
    fields: { annual_income: 540_000, loan_amount: 300_000, annuity: 9_000, goods_price: 280_000, years_employed: 6.5, ext_source_2: 0.71, ext_source_3: 0.66 },
    metrics: { loan_to_income: 0.56, payment_to_income: 0.2, income_mismatch_pct: null },
    output: {
      recommendation: "approve",
      confidence: 0.93,
      reasons: [
        "loan_to_income of 0.56 is well inside policy",
        "payment_to_income of 20% leaves comfortable headroom",
        "years_employed of 6.5 shows stable income",
      ],
      needs_human: false,
      human_question: null,
    },
  },
  {
    id: "b2e4d3c5-0002-4d2b-8e21-6b2c3d4e5f02",
    minutesAgo: 31,
    status: "needs_info",
    fields: { annual_income: 900_000, document_income: 720_000, loan_amount: 650_000, annuity: 21_000, goods_price: 600_000, years_employed: 3.2, ext_source_2: 0.58 },
    metrics: { loan_to_income: 0.72, payment_to_income: 0.28, income_mismatch_pct: 0.25 },
    output: {
      recommendation: "refer",
      confidence: 0.61,
      reasons: ["income_mismatch_pct of 25% between form and bank statement", "payment_to_income of 28% depends on which income is correct"],
      needs_human: true,
      human_question: "Which income figure is correct?",
    },
    question:
      "The income on your form (900,000.00) differs from the income on your document (720,000.00). Which figure is correct?",
  },
  {
    id: "c3f5e4d6-0003-4e3c-9d32-7c3d4e5f6a03",
    minutesAgo: 24,
    status: "pending_review",
    fields: { annual_income: 420_000, document_income: 410_000, loan_amount: 780_000, annuity: 14_500, goods_price: 700_000, years_employed: 1.1, ext_source_2: 0.44 },
    metrics: { loan_to_income: 1.86, payment_to_income: 0.41, income_mismatch_pct: 0.024 },
    output: {
      recommendation: "refer",
      confidence: 0.57,
      reasons: [
        "payment_to_income of 41% is close to the policy ceiling",
        "years_employed of 1.1 is short",
        "ext_source_1 and ext_source_3 are missing, so bureau evidence is thin",
      ],
      needs_human: true,
      human_question: "Is there a guarantor or additional income that offsets the short employment history?",
    },
  },
  {
    id: "d4a6f5e7-0004-4f4d-8c43-8d4e5f6a7b04",
    minutesAgo: 17,
    status: "pending_review",
    fields: { annual_income: 3_600_000, document_income: 3_550_000, loan_amount: 2_400_000, annuity: 62_000, goods_price: 2_300_000, years_employed: 11, ext_source_1: 0.74, ext_source_2: 0.79, ext_source_3: 0.7 },
    metrics: { loan_to_income: 0.67, payment_to_income: 0.21, income_mismatch_pct: 0.014 },
    output: {
      recommendation: "approve",
      confidence: 0.9,
      reasons: ["loan_to_income of 0.67 is within policy", "payment_to_income of 21% is affordable", "ext_source scores are all above 0.7"],
      needs_human: false,
      human_question: null,
    },
  },
  {
    id: "e5b7a6f8-0005-4a5e-9b54-9e5f6a7b8c05",
    minutesAgo: 9,
    status: "needs_info",
    fields: { annual_income: 610_000, loan_amount: 450_000, years_employed: 2 },
    metrics: null,
    output: null,
    question: "We need a few more details before we can assess your application: annuity, goods_price.",
  },
  {
    id: "f6c8b7a9-0006-4b6f-8a65-af6a7b8c9d06",
    minutesAgo: 5,
    status: "pending_review",
    fields: { annual_income: 300_000, document_income: 295_000, loan_amount: 1_150_000, annuity: 13_800, goods_price: 1_000_000, years_employed: 0.4, ext_source_2: 0.21 },
    metrics: { loan_to_income: 3.83, payment_to_income: 0.55, income_mismatch_pct: 0.017 },
    output: {
      recommendation: "decline",
      confidence: 0.84,
      reasons: ["payment_to_income of 55% exceeds the policy ceiling", "loan_to_income of 3.83 is high", "ext_source_2 of 0.21 is weak"],
      needs_human: true,
      human_question: "Confirm decline: affordability fails on payment_to_income.",
    },
  },
  {
    id: "a7d9c8ba-0007-4c7a-9b76-b07b8c9d0e07",
    minutesAgo: 75,
    status: "decided",
    fields: { annual_income: 480_000, document_income: 470_000, loan_amount: 520_000, annuity: 12_600, goods_price: 500_000, years_employed: 4, ext_source_2: 0.52 },
    metrics: { loan_to_income: 1.08, payment_to_income: 0.315, income_mismatch_pct: 0.021 },
    output: {
      recommendation: "decline",
      confidence: 0.66,
      reasons: ["payment_to_income of 31.5% is above the comfort band", "ext_source_1 and ext_source_3 are missing"],
      needs_human: true,
      human_question: "Is the payment affordable given the applicant's stable employment?",
    },
    decision: {
      decision: "approve",
      override: true,
      reason: "Four years with the same employer and a matching bank statement; payment is affordable.",
    },
  },
];

function seed(): void {
  for (const s of SEEDS) {
    const created = s.minutesAgo * MINUTE;
    const app: Application = {
      id: s.id,
      status: s.status,
      fields: { ...emptyFields(), ...s.fields },
      metrics: s.metrics,
      agent_output: s.output,
      created_at: iso(created),
      updated_at: iso(created - 2 * MINUTE),
    };
    applications.set(app.id, app);
    log(app.id, "applicant", "application_submitted", {}, iso(created));
    log(app.id, "agent", "status_changed", { from: "submitted", to: "analyzing" }, iso(created - 5_000));
    log(app.id, "agent", "fields_extracted", {}, iso(created - 20_000));
    if (s.metrics) log(app.id, "agent", "metrics_computed", { ...s.metrics }, iso(created - 22_000));
    if (s.output) {
      log(app.id, "agent", "reasoner_completed", {
        recommendation: s.output.recommendation,
        confidence: s.output.confidence,
      }, iso(created - 60_000));
    }
    const routedTo = s.status === "decided" ? "pending_review" : s.status;
    log(app.id, "router", "status_changed", {
      from: "analyzing",
      to: routedTo,
      ...(s.question ? { human_question: s.question } : {}),
    }, iso(created - 61_000));
    if (s.decision) {
      log(app.id, "reviewer", "decision_recorded", { ...s.decision }, iso(created - 20 * MINUTE));
      log(app.id, "reviewer", "status_changed", { from: "pending_review", to: "decided" }, iso(created - 20 * MINUTE));
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
  if (!app) throw new Error("Application not found");
  return app;
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
      fields: { ...emptyFields(), ...body },
      metrics: null,
      agent_output: null,
      created_at: now,
      updated_at: now,
    };
    applications.set(app.id, app);
    log(app.id, "applicant", "application_submitted", {});
    notify();

    setTimeout(() => setStatus(app, "analyzing"), ANALYZE_DELAY_MS);
    setTimeout(() => {
      const missing = REQUIRED_FIELDS.filter((name) => app.fields?.[name] == null);
      if (missing.length) {
        setStatus(app, "needs_info", "router", {
          human_question: `We need a few more details before we can assess your application: ${missing.join(", ")}.`,
        });
        return;
      }
      app.agent_output = fallbackOutput();
      setStatus(app, "pending_review", "router");
    }, ROUTE_DELAY_MS);

    return { id: app.id, status: app.status };
  },

  async reply(id, body) {
    const app = mustGet(id);
    if (app.status !== "needs_info") throw new Error("This application is not waiting for information");
    log(id, "applicant", "applicant_replied", { answer: body.answer });
    setStatus(app, "analyzing");
    setTimeout(() => {
      app.agent_output ??= fallbackOutput();
      setStatus(app, "pending_review", "router");
    }, ROUTE_DELAY_MS - ANALYZE_DELAY_MS);
  },

  async decide(id, body) {
    const app = mustGet(id);
    if (app.status !== "pending_review" && app.status !== "auto_cleared") {
      throw new Error(`Cannot decide an application in status ${app.status}`);
    }
    if ((body.decision === "reject" || body.override) && !body.reason?.trim()) {
      throw new Error("A reason is required to reject or override");
    }
    log(id, "reviewer", "decision_recorded", { ...body });
    setStatus(app, "decided", "reviewer");
  },
};
