-- Perspectome database, version 1.
--
-- One schema per track, so access follows ownership:
--   personas    Track A writes, everyone reads       (conditioning fields only)
--   heldout     Track A writes, ONLY Track C reads   (methodology invariant)
--   sim         Track B writes, C and D read
--   validation  Track C writes, D reads
--   app         Track D's site (accounts, chats)
--
-- Category values (age bands, held-out items, ...) are NOT re-typed here as
-- CHECK constraints: src/common/schema.py is the single source of truth
-- (rule 26) and src/common/db.py validates against it before writing.
-- Held-out answers are stored long (one row per persona x item), so changing
-- the held-out item list never needs a migration.

create schema if not exists meta;
create schema if not exists personas;
create schema if not exists heldout;
create schema if not exists sim;
create schema if not exists validation;
create schema if not exists app;

create table if not exists meta.schema_migrations (
    version    text primary key,
    applied_at timestamptz not null default now()
);

-- Track A ---------------------------------------------------------------------

create table if not exists personas.persona_sets (
    persona_set_hash text primary key,          -- "sha256:<hex>" of personas.csv (Track A's frozen hash)
    personas_csv     bytea not null,            -- the exact file bytes, so a pulled copy keeps the same hash
    seed             integer,
    source           text not null,             -- e.g. "WVS-7 Turkey + Eurostat margins"
    n_personas       integer not null,
    created_by       text not null default current_user,
    created_at       timestamptz not null default now(),
    notes            text
);

create table if not exists personas.personas (
    persona_set_hash  text not null references personas.persona_sets on delete cascade,
    persona_id        text not null,
    cell_id           text,
    weight            double precision not null,
    age_band          text,
    gender            text,
    education_level   text,
    region            text,
    settlement_type   text,
    marital_status    text,
    employment_status text,
    income_decile     smallint,
    primary key (persona_set_hash, persona_id)
);
create index if not exists personas_cell_idx on personas.personas (persona_set_hash, cell_id);

create table if not exists heldout.answers (
    persona_set_hash text not null,
    persona_id       text not null,
    item             text not null,             -- a schema.HELDOUT_FIELDS name
    value            text,                      -- raw label ("7", "quite_a_lot"); null = missing
    primary key (persona_set_hash, persona_id, item),
    foreign key (persona_set_hash, persona_id)
        references personas.personas (persona_set_hash, persona_id) on delete cascade
);

-- Track B ---------------------------------------------------------------------

create table if not exists sim.runs (
    id               bigserial primary key,
    run_id           text not null,
    run_type         text not null,
    scenario_id      text not null,
    target_item      text,
    model            text,
    model_snapshot   text not null,
    seed             integer,
    persona_set_hash text not null references personas.persona_sets,
    n_personas       integer,
    result           jsonb not null,            -- the full results.json document
    created_by       text not null default current_user,
    created_at       timestamptz not null default now(),
    unique (run_id, model_snapshot, persona_set_hash)
);
create index if not exists runs_scenario_idx on sim.runs (scenario_id, model_snapshot);

-- Track C ---------------------------------------------------------------------

create table if not exists validation.reports (
    id               bigserial primary key,
    persona_set_hash text,
    report           jsonb not null,            -- the full comparison.json document
    created_by       text not null default current_user,
    created_at       timestamptz not null default now()
);

-- Track D ---------------------------------------------------------------------

create table if not exists app.users (
    name       text primary key,
    salt       text not null,
    hash       text not null,
    created_at timestamptz not null default now()
);

create table if not exists app.chats (
    owner      text not null references app.users on delete cascade,
    chat_id    text not null,
    data       jsonb not null,
    updated_at timestamptz not null default now(),
    primary key (owner, chat_id)
);

-- Roles -------------------------------------------------------------------------
-- Group roles (no login). Personal login roles are created by
-- `python -m src.common.db create-users` and granted one of these.

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'track_a') then create role track_a nologin; end if;
    if not exists (select 1 from pg_roles where rolname = 'track_b') then create role track_b nologin; end if;
    if not exists (select 1 from pg_roles where rolname = 'track_c') then create role track_c nologin; end if;
    if not exists (select 1 from pg_roles where rolname = 'track_d') then create role track_d nologin; end if;
end $$;

-- Nobody gets anything by default (Supabase's API roles included).
revoke all on schema meta, personas, heldout, sim, validation, app from public;
do $$
declare r text;
begin
    foreach r in array array['anon', 'authenticated'] loop
        if exists (select 1 from pg_roles where rolname = r) then
            execute format('revoke all on schema meta, personas, heldout, sim, validation, app from %I', r);
            execute format('revoke all on all tables in schema personas, heldout, sim, validation, app from %I', r);
        end if;
    end loop;
end $$;

grant usage on schema meta to track_a, track_b, track_c, track_d;
grant select on meta.schema_migrations to track_a, track_b, track_c, track_d;

-- personas: A writes, everyone reads
grant usage on schema personas to track_a, track_b, track_c, track_d;
grant select on all tables in schema personas to track_a, track_b, track_c, track_d;
grant insert, update, delete on all tables in schema personas to track_a;

-- heldout: A writes, only C reads. B and D get no usage on the schema at all.
grant usage on schema heldout to track_a, track_c;
grant insert, update, delete on heldout.answers to track_a;
grant select on heldout.answers to track_c;

-- sim: B writes, C and D read
grant usage on schema sim to track_b, track_c, track_d;
grant select on all tables in schema sim to track_b, track_c, track_d;
grant insert, update, delete on all tables in schema sim to track_b;
grant usage on all sequences in schema sim to track_b;

-- validation: C writes, D reads
grant usage on schema validation to track_c, track_d;
grant select on all tables in schema validation to track_c, track_d;
grant insert, update, delete on all tables in schema validation to track_c;
grant usage on all sequences in schema validation to track_c;

-- app: D only
grant usage on schema app to track_d;
grant select, insert, update, delete on all tables in schema app to track_d;
