-- One row per research run: what was asked, what was read, every draft and
-- its critique, and the final report.
create table if not exists runs (
    id            uuid primary key,
    topic         text        not null,
    created_at    timestamptz not null default now(),
    status        text        not null check (status in ('running', 'done', 'error')),
    client_hash   text,
    final_report  text,
    final_score   int,
    drafts        jsonb       not null default '[]'::jsonb,
    sources       jsonb       not null default '[]'::jsonb,
    queries       jsonb       not null default '[]'::jsonb,
    elapsed_s     real,
    error         text
);

-- Serves the per-client hourly limit, which counts recent rows for one hash.
create index if not exists runs_client_hash_created_at_idx
    on runs (client_hash, created_at desc);
