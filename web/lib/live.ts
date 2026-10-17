// Live data source: reads from Supabase (realtime for applications), writes through the agent API.

import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { API_URL, SUPABASE_ANON_KEY, SUPABASE_URL } from "./config";
import { ApiError } from "./errors";
import type {
  Application,
  AuditEvent,
  CreateApplicationRequest,
  CreateApplicationResponse,
  DecisionRequest,
  ReplyRequest,
} from "./types";
import type { DataSource } from "./data";

let client: SupabaseClient | null = null;

function supabase(): SupabaseClient {
  client ??= createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  return client;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail: unknown = await res.json().catch(() => null);
    const message =
      detail && typeof detail === "object" && "detail" in detail && typeof detail.detail === "string"
        ? detail.detail
        : `Request failed (${res.status})`;
    throw new ApiError(message, res.status);
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

  createApplication: (body: CreateApplicationRequest) =>
    post<CreateApplicationResponse>("/applications", body),

  reply: (id: string, body: ReplyRequest) => post<unknown>(`/applications/${id}/reply`, body).then(() => undefined),

  decide: (id: string, body: DecisionRequest) =>
    post<unknown>(`/applications/${id}/decision`, body).then(() => undefined),
};
