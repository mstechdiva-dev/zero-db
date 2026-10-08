-- SchemaZero — complete Supabase database schema (final state)
--
-- Run this ONE file in the Supabase SQL editor. It already includes everything
-- that migrations 001 to 007 add, so a new database needs nothing else.
--
-- Not a blank database? If you already have tables from an older or different
-- schema, run supabase/reset.sql first (it keeps the waitlist, sales leads and
-- saved agent prompts), then this file.
--
-- The code reads and writes exactly these tables and columns. The test in
-- apps/agent/tests/test_schema_matches_code.py checks that against a real
-- Postgres, including who can see and change what.

-- Stop early, with a clear message, if the tables are already there.
do $$
begin
  if to_regclass('public.organizations') is not null then
    raise exception 'SchemaZero tables already exist in this database. To start over, run supabase/reset.sql first, then this file.';
  end if;
end $$;

-- ============================================================
-- Extensions
-- ============================================================
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- ============================================================
-- Enums
-- ============================================================
create type plan_type as enum ('trial', 'solo', 'teams', 'enterprise');
create type user_role as enum ('owner', 'admin', 'member');
create type db_engine as enum (
  'postgresql',
  'supabase',
  'neon',
  'cockroachdb',
  'mysql',
  'mariadb',
  'mongodb',
  'redis',
  'sqlserver',
  'sqlite',
  'oracle',
  'snowflake',
  'dynamodb'
);
create type change_type as enum (
  'table_added',
  'table_dropped',
  'column_added',
  'column_dropped',
  'column_modified',
  'index_added',
  'index_dropped',
  'constraint_added',
  'constraint_dropped',
  'type_changed',
  'nullable_changed',
  'default_changed',
  'collection_added',
  'collection_dropped',
  'validation_changed',
  'key_pattern_added',
  'key_pattern_dropped',
  'ttl_changed',
  'primary_key_changed',
  'foreign_key_dropped',
  -- names Scout writes (also added to existing databases by migration 006)
  'table_created',
  'index_created',
  'key_type_changed',
  'ttl_policy_changed'
);
create type risk_level as enum ('low', 'medium', 'high', 'critical');
create type alert_channel as enum ('webhook', 'slack', 'pagerduty', 'email');
create type notification_status as enum ('sent', 'failed', 'skipped');

-- ============================================================
-- Organizations
-- ============================================================
create table organizations (
  id                    uuid primary key default uuid_generate_v4(),
  name                  text not null,
  plan                  plan_type not null default 'trial',
  trial_starts_at       timestamptz not null default now(),
  trial_ends_at         timestamptz not null default (now() + interval '14 days'),
  trial_converted       boolean not null default false,
  stripe_customer_id    text,
  stripe_subscription_id text,
  created_at            timestamptz not null default now()
);

-- ============================================================
-- Users
-- ============================================================
create table users (
  id            uuid primary key default uuid_generate_v4(),
  auth_user_id  uuid not null unique references auth.users(id) on delete cascade,
  org_id        uuid not null references organizations(id) on delete cascade,
  email         text not null,
  role          user_role not null default 'member',
  created_at    timestamptz not null default now()
);

create index users_org_id_idx on users(org_id);
create index users_auth_user_id_idx on users(auth_user_id);

-- ============================================================
-- Connected Databases
-- ============================================================
create table connected_databases (
  id                          uuid primary key default uuid_generate_v4(),
  org_id                      uuid not null references organizations(id) on delete cascade,
  engine                      db_engine not null,
  display_name                text not null,
  encrypted_connection_string text not null,
  is_active                   boolean not null default true,
  created_at                  timestamptz not null default now()
);

create index connected_databases_org_id_idx on connected_databases(org_id);

-- ============================================================
-- Scout Heartbeat
-- ============================================================
create table scout_heartbeat (
  id          uuid primary key default uuid_generate_v4(),
  database_id uuid not null references connected_databases(id) on delete cascade,
  last_seen   timestamptz not null default now(),
  created_at  timestamptz not null default now(),
  unique(database_id)
);

-- ============================================================
-- Change Events
-- ============================================================
create table change_events (
  id           uuid primary key default uuid_generate_v4(),
  org_id       uuid not null references organizations(id) on delete cascade,
  database_id  uuid not null references connected_databases(id) on delete cascade,
  change_type  change_type not null,
  object_type  text not null,
  object_name  text not null,
  schema_name  text,
  before_state jsonb,
  after_state  jsonb,
  risk_level   risk_level,
  detected_at  timestamptz not null default now()
);

create index change_events_org_id_idx on change_events(org_id);
create index change_events_database_id_idx on change_events(database_id);
create index change_events_detected_at_idx on change_events(detected_at desc);
create index change_events_risk_level_idx on change_events(risk_level);

-- ============================================================
-- Impact Analysis
-- ============================================================
create table impact_analysis (
  id               uuid primary key default uuid_generate_v4(),
  change_event_id  uuid not null references change_events(id) on delete cascade,
  affected_queries jsonb not null default '[]',
  affected_services jsonb not null default '[]',
  affected_indexes jsonb not null default '[]',
  summary          text not null,
  recommendations  jsonb not null default '[]',
  next_action      text,
  raw_claude_response text,
  created_at       timestamptz not null default now(),
  unique(change_event_id)
);

-- ============================================================
-- Alert Configs
-- ============================================================
create table alert_configs (
  id                  uuid primary key default uuid_generate_v4(),
  org_id              uuid not null references organizations(id) on delete cascade,
  webhook_url         text,
  slack_webhook_url   text,
  pagerduty_api_key   text,
  email_recipients    jsonb not null default '[]',
  notify_on           jsonb not null default '["high", "critical"]',
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique(org_id)
);

-- ============================================================
-- Notification Log
-- ============================================================
create table notification_log (
  id              uuid primary key default uuid_generate_v4(),
  org_id          uuid not null references organizations(id) on delete cascade,
  change_event_id uuid references change_events(id) on delete set null,
  channel         alert_channel not null,
  status          notification_status not null,
  error_message   text,
  sent_at         timestamptz not null default now()
);

create index notification_log_org_id_idx on notification_log(org_id);
create index notification_log_change_event_id_idx on notification_log(change_event_id);

-- ============================================================
-- Row-Level Security
-- ============================================================
alter table organizations enable row level security;
alter table users enable row level security;
alter table connected_databases enable row level security;
alter table scout_heartbeat enable row level security;
alter table change_events enable row level security;
alter table impact_analysis enable row level security;
alter table alert_configs enable row level security;
alter table notification_log enable row level security;

-- scout_heartbeat: users can read heartbeats for databases in their org
create policy "users_select_own_scout_heartbeat" on scout_heartbeat
  for select using (
    database_id in (
      select id from connected_databases where org_id in (
        select org_id from users where auth_user_id = auth.uid()
      )
    )
  );

-- Users can only read their own org
create policy "users_select_own_org" on organizations
  for select using (
    id in (
      select org_id from users where auth_user_id = auth.uid()
    )
  );

create policy "users_select_own_user" on users
  for select using (auth_user_id = auth.uid());

create policy "users_select_own_databases" on connected_databases
  for select using (
    org_id in (
      select org_id from users where auth_user_id = auth.uid()
    )
  );

create policy "users_select_own_change_events" on change_events
  for select using (
    org_id in (
      select org_id from users where auth_user_id = auth.uid()
    )
  );

create policy "users_select_own_impact" on impact_analysis
  for select using (
    change_event_id in (
      select id from change_events where org_id in (
        select org_id from users where auth_user_id = auth.uid()
      )
    )
  );

create policy "users_select_own_alert_config" on alert_configs
  for select using (
    org_id in (
      select org_id from users where auth_user_id = auth.uid()
    )
  );

create policy "users_update_own_alert_config" on alert_configs
  for update using (
    org_id in (
      select org_id from users where auth_user_id = auth.uid()
    )
  )
  with check (
    org_id in (
      select org_id from users where auth_user_id = auth.uid()
    )
  );

create policy "users_insert_own_alert_config" on alert_configs
  for insert with check (
    org_id in (
      select org_id from users where auth_user_id = auth.uid()
    )
  );

create policy "users_select_own_notification_log" on notification_log
  for select using (
    org_id in (
      select org_id from users where auth_user_id = auth.uid()
    )
  );

-- ============================================================
-- Functions
-- ============================================================

-- Trigger to keep alert_configs.updated_at current
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger alert_configs_updated_at
  before update on alert_configs
  for each row execute procedure set_updated_at();

-- Called on signup to provision org + user record
create or replace function handle_new_user()
returns trigger language plpgsql security definer
set search_path = public, auth
as $$
declare
  new_org_id uuid;
begin
  insert into organizations (name)
    values (coalesce(new.raw_user_meta_data->>'org_name', split_part(new.email, '@', 1)))
    returning id into new_org_id;

  insert into users (auth_user_id, org_id, email, role)
    values (new.id, new_org_id, new.email, 'owner');

  insert into alert_configs (org_id)
    values (new_org_id);

  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure handle_new_user();

-- ============================================================
-- Dashboard: pause and delete databases
-- The dashboard pauses and deletes databases with the signed-in user's own
-- login. Without these, those buttons would quietly do nothing.
-- Adding a database is NOT allowed this way: it goes through the backend,
-- which tests the connection first.
-- ============================================================
create policy "users_update_own_databases" on connected_databases
  for update using (
    org_id in (select org_id from users where auth_user_id = auth.uid())
  )
  with check (
    org_id in (select org_id from users where auth_user_id = auth.uid())
  );

create policy "users_delete_own_databases" on connected_databases
  for delete using (
    org_id in (select org_id from users where auth_user_id = auth.uid())
  );

-- Column limits: signed-in users can never read the stored connection string
-- (even their own) and can only change the name and the paused flag.
-- The backend uses the service role, which is not affected.
revoke select, update on connected_databases from anon, authenticated;
grant select (id, org_id, engine, display_name, is_active, created_at)
  on connected_databases to authenticated;
grant update (display_name, is_active) on connected_databases to authenticated;

-- ============================================================
-- Leads (admin only): qualified sales leads captured by the Sal agent
-- No policies on purpose: only the service role can read or write.
-- ============================================================
create table if not exists leads (
  id           uuid        primary key default gen_random_uuid(),
  org_id       uuid        references organizations(id) on delete set null,
  user_email   text,
  conversation jsonb       not null default '[]',
  sal_summary  text,
  created_at   timestamptz not null default now()
);
create index if not exists leads_org_id_idx on leads(org_id);
create index if not exists leads_created_at_idx on leads(created_at desc);
alter table leads enable row level security;

-- ============================================================
-- Agent skills (admin only): agent prompts edited in the admin panel.
-- The backend reads these before falling back to the files in agents/.
-- ============================================================
create table if not exists agent_skills (
  name       text primary key,
  content    text not null,
  saved_by   text,
  updated_at timestamptz not null default now()
);
alter table agent_skills enable row level security;
drop policy if exists "deny_all" on agent_skills;
create policy "deny_all" on agent_skills
  for all to authenticated, anon using (false);

-- ============================================================
-- Waitlist: the landing page "Join waitlist" form (service role only)
-- ============================================================
create table if not exists waitlist (
  id         uuid primary key default gen_random_uuid(),
  email      text not null unique,
  created_at timestamptz not null default now()
);
alter table waitlist enable row level security;

-- ============================================================
-- Live updates: the dashboard change feed listens for new change events.
-- (Supabase only sends live updates for tables in this publication.)
-- ============================================================
do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime')
     and not exists (select 1 from pg_publication_tables
                     where pubname = 'supabase_realtime' and tablename = 'change_events') then
    alter publication supabase_realtime add table change_events;
  end if;
end $$;

-- ============================================================
-- Existing accounts: give anyone who signed up before this schema existed
-- an organization, a user record and alert settings, the same as a new
-- signup gets. Does nothing on a new project. Safe to run again.
-- ============================================================
do $$
declare
  r record;
  new_org_id uuid;
begin
  for r in
    select u.id, u.email, u.raw_user_meta_data
    from auth.users u
    where not exists (select 1 from public.users x where x.auth_user_id = u.id)
  loop
    insert into organizations (name)
      values (coalesce(r.raw_user_meta_data->>'org_name', split_part(r.email, '@', 1)))
      returning id into new_org_id;
    insert into users (auth_user_id, org_id, email, role)
      values (r.id, new_org_id, coalesce(r.email, ''), 'owner');
    insert into alert_configs (org_id) values (new_org_id);
  end loop;
end $$;
