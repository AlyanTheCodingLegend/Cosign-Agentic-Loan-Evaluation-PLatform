import { IS_DEMO_MODE } from "./config";
import { demoSource } from "./demo";
import { liveSource } from "./live";
import type {
  Application,
  ApplicationAccepted,
  AuditEvent,
  CreateApplicationRequest,
  DecisionRequest,
  ReplyRequest,
} from "./types";

/** Everything the screens read and write. Live talks to Supabase + the API; demo is in memory. */
export interface DataSource {
  listApplications(): Promise<Application[]>;
  getApplication(id: string): Promise<Application | null>;
  listAuditEvents(id: string): Promise<AuditEvent[]>;
  /** Calls onChange whenever any application row changes. Returns an unsubscribe function. */
  subscribe(onChange: () => void): () => void;
  createApplication(body: CreateApplicationRequest): Promise<ApplicationAccepted>;
  reply(id: string, body: ReplyRequest): Promise<ApplicationAccepted>;
  decide(id: string, body: DecisionRequest): Promise<void>;
}

export const data: DataSource = IS_DEMO_MODE ? demoSource : liveSource;
