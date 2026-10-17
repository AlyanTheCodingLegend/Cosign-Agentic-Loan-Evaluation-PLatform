"use client";

import { useCallback, useEffect, useState } from "react";
import { data } from "./data";
import { errorMessage } from "./errors";
import type { Application, AuditEvent } from "./types";

interface Query<T> {
  data: T | undefined;
  error: string | null;
  loading: boolean;
}

/** Loads with `load`, then reloads whenever any application changes (Supabase realtime). */
function useLiveQuery<T>(key: string, load: () => Promise<T>): Query<T> {
  const [state, setState] = useState<Query<T> & { key: string }>({
    key,
    data: undefined,
    error: null,
    loading: true,
  });

  const run = useCallback(() => {
    load().then(
      (value) => setState({ key, data: value, error: null, loading: false }),
      (err: unknown) => setState((s) => ({ ...s, key, error: errorMessage(err), loading: false })),
    );
    // `key` identifies the query; `load` is a fresh closure every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    run();
    return data.subscribe(run);
  }, [run]);

  // Never show the previous key's data while a new key loads.
  if (state.key !== key) return { data: undefined, error: null, loading: true };
  return state;
}

export function useApplications(): Query<Application[]> {
  return useLiveQuery("applications", () => data.listApplications());
}

export function useApplicationCase(id: string): Query<{ app: Application | null; events: AuditEvent[] }> {
  return useLiveQuery(`case:${id}`, async () => {
    const [app, events] = await Promise.all([data.getApplication(id), data.listAuditEvents(id)]);
    return { app, events };
  });
}
