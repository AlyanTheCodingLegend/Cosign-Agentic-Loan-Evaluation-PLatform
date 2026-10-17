-- Row-level security for the browser (anon key). Run once in the Supabase SQL editor after schema.sql.
-- The API uses the service role key, which bypasses RLS, so it is unaffected.
--
-- The web app reads the reviewer queue (applications, realtime) and the case audit trail
-- (audit_log) directly. Every write goes through the API. With RLS on and no insert, update or
-- delete policies, the anon key can read those two tables and change nothing. override_log has
-- no policy at all, so the anon key cannot see or touch it.

alter table applications enable row level security;
alter table audit_log enable row level security;
alter table override_log enable row level security;

create policy "anon can read applications" on applications
    for select to anon using (true);

create policy "anon can read audit log" on audit_log
    for select to anon using (true);
