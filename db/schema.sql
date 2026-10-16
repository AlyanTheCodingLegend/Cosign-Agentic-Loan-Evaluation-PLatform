-- Loan approval agent schema (Postgres / Supabase).
-- Owner: Alyan. Mirrors api/app/models/status.py and contract.py; change them together.
-- audit_log and override_log are append-only: UPDATE, DELETE and TRUNCATE are blocked.

create table applications (
    id uuid primary key default gen_random_uuid(),
    status text not null default 'submitted'
        check (status in (
            'submitted', 'analyzing', 'needs_info', 'pending_review', 'auto_cleared', 'decided'
        )),
    fields jsonb,
    metrics jsonb,
    agent_output jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create function set_updated_at() returns trigger
language plpgsql as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

create trigger applications_set_updated_at
    before update on applications
    for each row execute function set_updated_at();

create table audit_log (
    id bigint generated always as identity primary key,
    application_id uuid not null references applications (id),
    actor text not null,
    event_type text not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table override_log (
    id bigint generated always as identity primary key,
    application_id uuid not null references applications (id),
    agent_recommendation text not null
        check (agent_recommendation in ('approve', 'decline', 'refer')),
    human_decision text not null
        check (human_decision in ('approve', 'reject')),
    reason text not null check (length(btrim(reason)) > 0),
    created_at timestamptz not null default now()
);

create function block_log_mutation() returns trigger
language plpgsql as $$
begin
    raise exception '% is append-only: % is not allowed', tg_table_name, tg_op;
end;
$$;

create trigger audit_log_append_only
    before update or delete on audit_log
    for each row execute function block_log_mutation();

create trigger audit_log_no_truncate
    before truncate on audit_log
    for each statement execute function block_log_mutation();

create trigger override_log_append_only
    before update or delete on override_log
    for each row execute function block_log_mutation();

create trigger override_log_no_truncate
    before truncate on override_log
    for each statement execute function block_log_mutation();

-- Reviewer queue and status reads come from Supabase realtime on this table.
alter publication supabase_realtime add table applications;
