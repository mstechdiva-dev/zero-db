-- SchemaZero — Supabase Database Schema
-- Run this in your Supabase SQL editor to initialize the database.

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
  'foreign_key_dropped'
);
create type risk_level as enum ('low', 'medium', 'high', 'critical');
create type alert_channel as enum ('slack', 'pagerduty', 'email');
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

-- Called on signup to provision org + user record
create or replace function handle_new_user()
returns trigger language plpgsql security definer as $$
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
