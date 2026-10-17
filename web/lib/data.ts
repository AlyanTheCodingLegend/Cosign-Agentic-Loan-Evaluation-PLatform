import { IS_DEMO_MODE } from "./config";
import { demoSource } from "./demo";
import { liveSource } from "./live";
import type {
  Application,
  AuditEvent,
  CreateApplicationRequest,
  CreateApplicationResponse,
  DecisionRequest,
  HumanDecision,
  ReplyRequest,
} from "./types";

/** Everything the screens read and write. Live talks to Supabase + the API; demo is in memory. */
export interface DataSource {
  listApplications(): Promise<Application[]>;
  getApplication(id: string): Promise<Application | null>;
  listAuditEvents(id: string): Promise<AuditEvent[]>;
  /** Calls onChange whenever any application row changes. Returns an unsubscribe function. */
  subscribe(onChange: () => void): () => void;
  createApplication(body: CreateApplicationRequest): Promise<CreateApplicationResponse>;
  reply(id: string, body: ReplyRequest): Promise<void>;
  decide(id: string, body: DecisionRequest): Promise<void>;
}

export const data: DataSource = IS_DEMO_MODE ? demoSource : liveSource;

/**
 * The open question for the applicant. The router's question (income mismatch, missing fields)
 * is not a column on applications, so it is read from the latest audit event that carries one.
 */
export function openQuestion(app: Application, events: AuditEvent[]): string | null {
  if (app.status !== "needs_info") return null;
  for (let i = events.length - 1; i >= 0; i--) {
    const q = events[i].payload.human_question;
    if (typeof q === "string" && q) return q;
  }
  return app.agent_output?.human_question ?? null;
}

/** The reviewer's final decision, read from the audit log (applications has no decision column). */
export function finalDecision(events: AuditEvent[]): { decision: HumanDecision; reason: string | null } | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const { decision, reason } = events[i].payload;
    if (decision === "approve" || decision === "reject") {
      return { decision, reason: typeof reason === "string" ? reason : null };
    }
  }
  return null;
}
