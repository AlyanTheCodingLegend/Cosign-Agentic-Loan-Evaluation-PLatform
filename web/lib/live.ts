// Live data source: reads from Supabase (realtime for applications), writes through the agent API.

import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { API_URL, SUPABASE_ANON_KEY, SUPABASE_URL } from "./config";
import { ApiError } from "./errors";
import type {
  Application,
  ApplicationAccepted,
  AuditEvent,
  CreateApplicationRequest,
  DecisionRequest,
  ReplyRequest,
} from "./types";
import type { DataSource } from "./data";

let client: SupabaseClient | null = null;

function supabase(): SupabaseClient {
  client ??= createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  return client;
}

/** FastAPI errors carry `detail`: a string for HTTPException, a list for validation errors. */
function detailMessage(body: unknown): string | null {
  if (!body || typeof body !== "object" || !("detail" in body)) return null;
  const { detail } = body;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d: unknown) => (d && typeof d === "object" && "msg" in d && typeof d.msg === "string" ? d.msg : null))
      .filter((m): m is string => m !== null);
    return messages.length ? messages.join("; ") : null;
  }
  return null;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errorBody: unknown = await res.json().catch(() => null);
    throw new ApiError(detailMessage(errorBody) ?? `Request failed (${res.status})`, res.status);
  }
  return (await res.json()) as T;
}

export const liveSource: DataSource = {
  async listApplications() {
    const { data, error } = await supabase()
      .from("applications")
      .select("*")
      .order("created_at", { ascending: false });
    if (error) throw new Error(error.message);
    return data as Application[];
  },

  async getApplication(id) {
    const { data, error } = await supabase().from("applications").select("*").eq("id", id).maybeSingle();
    if (error) throw new Error(error.message);
    return data as Application | null;
  },

  async listAuditEvents(id) {
    const { data, error } = await supabase()
      .from("audit_log")
      .select("*")
      .eq("application_id", id)
      .order("created_at", { ascending: true });
    if (error) throw new Error(error.message);
    return data as AuditEvent[];
  },

  subscribe(onChange) {
    const channel = supabase()
      .channel("applications-changes")
      .on("postgres_changes", { event: "*", schema: "public", table: "applications" }, onChange)
      .subscribe();
    return () => {
      void supabase().removeChannel(channel);
    };
  },

  createApplication: (body: CreateApplicationRequest) => post<ApplicationAccepted>("/applications", body),

  reply: (id: string, body: ReplyRequest) => post<ApplicationAccepted>(`/applications/${id}/reply`, body),

  decide: (id: string, body: DecisionRequest) =>
    post<unknown>(`/applications/${id}/decision`, body).then(() => undefined),
};
