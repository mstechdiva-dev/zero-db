-- ============================================================
-- SchemaZero — Supabase Database Schema
-- Run this in Supabase SQL Editor
-- ============================================================

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ============================================================
-- ORGANIZATIONS
-- ============================================================
create table organizations (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  slug text unique not null,
  plan text not null default 'trial' check (plan in ('trial', 'solo', 'teams', 'enterprise')),
  trial_starts_at timestamptz default now(),
  trial_ends_at timestamptz default (now() + interval '14 days'),
  trial_converted boolean default false,
  stripe_customer_id text,
  stripe_subscription_id text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================================
-- USERS
-- ============================================================
create table users (
  id uuid primary key references auth.users(id) on delete cascade,
  org_id uuid references organizations(id) on delete cascade,
  email text not null,
  full_name text,
  role text not null default 'member' check (role in ('owner', 'admin', 'member')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================================
-- CONNECTED DATABASES
-- ============================================================
create table connected_databases (
  id uuid primary key default uuid_generate_v4(),
  org_id uuid references organizations(id) on delete cascade,
  name text not null,
  engine text not null check (engine in (
    'postgresql',
    'mysql',
    'mongodb',
    'redis',
    'sqlserver',
    'sqlite',
    'oracle',
    'mariadb',
    'snowflake',
    'dynamodb',
    'cockroachdb',
    'neon',
    'supabase',
    'other'
  )),
  host text not null,
  port integer,
  database_name text,
  username text,
  connection_string_encrypted text not null,
  ssl_enabled boolean default true,
  is_active boolean default true,
  last_connected_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================================
-- SCHEMA SNAPSHOTS
-- Before and after DDL captures per connected database
-- ============================================================
create table schema_snapshots (
  id uuid primary key default uuid_generate_v4(),
  database_id uuid references connected_databases(id) on delete cascade,
  snapshot jsonb not null,
  captured_at timestamptz default now()
);

-- ============================================================
-- CHANGE EVENTS
-- Every schema change detected by Scout
-- ============================================================
create table change_events (
  id uuid primary key default uuid_generate_v4(),
  database_id uuid references connected_databases(id) on delete cascade,
  org_id uuid references organizations(id) on delete cascade,
  change_type text not null check (change_type in (
    'column_added',
    'column_dropped',
    'column_modified',
    'table_added',
    'table_dropped',
    'index_added',
    'index_dropped',
    'constraint_added',
    'constraint_dropped',
    'type_changed',
    'key_pattern_added',
    'key_pattern_dropped',
    'key_pattern_modified',
    'other'
  )),
  object_type text not null,
  object_name text not null,
  schema_name text,
  before_state jsonb,
  after_state jsonb,
  risk_level text not null default 'low' check (risk_level in ('low', 'medium', 'high', 'critical')),
  risk_reason text,
  resolved boolean default false,
  resolved_at timestamptz,
  detected_at timestamptz default now(),
  created_at timestamptz default now()
);

-- ============================================================
-- IMPACT ANALYSIS
-- Zero's analysis results for each change event
-- ============================================================
create table impact_analysis (
  id uuid primary key default uuid_generate_v4(),
  change_event_id uuid references change_events(id) on delete cascade,
  affected_queries jsonb,
  affected_services jsonb,
  affected_indexes jsonb,
  summary text,
  recommendations jsonb,
  analyzed_by text default 'zero',
  analyzed_at timestamptz default now()
);

-- ============================================================
-- ALERT CONFIGURATIONS
-- Per org notification settings
-- ============================================================
create table alert_configs (
  id uuid primary key default uuid_generate_v4(),
  org_id uuid references organizations(id) on delete cascade,
  channel text not null check (channel in ('slack', 'email', 'pagerduty', 'webhook')),
  config jsonb not null,
  enabled boolean default true,
  notify_on text[] default array['high', 'critical'],
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================================
-- NOTIFICATION LOG
-- Record of every alert sent
-- ============================================================
create table notification_log (
  id uuid primary key default uuid_generate_v4(),
  org_id uuid references organizations(id) on delete cascade,
  change_event_id uuid references change_events(id) on delete cascade,
  channel text not null,
  status text not null check (status in ('sent', 'failed', 'pending')),
  payload jsonb,
  error text,
  sent_at timestamptz default now()
);

-- ============================================================
-- SCOUT HEARTBEAT
-- Tracks Scout agent health per connected database
-- ============================================================
create table scout_heartbeat (
  id uuid primary key default uuid_generate_v4(),
  database_id uuid references connected_databases(id) on delete cascade,
  status text not null check (status in ('watching', 'disconnected', 'error')),
  last_seen_at timestamptz default now(),
  error_message text
);

-- ============================================================
-- INDEXES
-- ============================================================
create index idx_change_events_database_id on change_events(database_id);
create index idx_change_events_org_id on change_events(org_id);
create index idx_change_events_detected_at on change_events(detected_at desc);
create index idx_change_events_risk_level on change_events(risk_level);
create index idx_schema_snapshots_database_id on schema_snapshots(database_id);
create index idx_impact_analysis_change_event_id on impact_analysis(change_event_id);
create index idx_notification_log_org_id on notification_log(org_id);
create index idx_connected_databases_org_id on connected_databases(org_id);
create index idx_scout_heartbeat_database_id on scout_heartbeat(database_id);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
alter table organizations enable row level security;
alter table users enable row level security;
alter table connected_databases enable row level security;
alter table schema_snapshots enable row level security;
alter table change_events enable row level security;
alter table impact_analysis enable row level security;
alter table alert_configs enable row level security;
alter table notification_log enable row level security;
alter table scout_heartbeat enable row level security;

-- Users can only see their own org
create policy "users see own org" on organizations
  for select using (
    id in (select org_id from users where id = auth.uid())
  );

create policy "users see own profile" on users
  for select using (id = auth.uid());

create policy "users see own org databases" on connected_databases
  for all using (
    org_id in (select org_id from users where id = auth.uid())
  );

create policy "users see own org changes" on change_events
  for select using (
    org_id in (select org_id from users where id = auth.uid())
  );

create policy "users see own org snapshots" on schema_snapshots
  for select using (
    database_id in (
      select id from connected_databases
      where org_id in (select org_id from users where id = auth.uid())
    )
  );

create policy "users see own org impact" on impact_analysis
  for select using (
    change_event_id in (
      select id from change_events
      where org_id in (select org_id from users where id = auth.uid())
    )
  );

create policy "users see own org alerts" on alert_configs
  for all using (
    org_id in (select org_id from users where id = auth.uid())
  );

create policy "users see own org notifications" on notification_log
  for select using (
    org_id in (select org_id from users where id = auth.uid())
  );

create policy "users see own scout status" on scout_heartbeat
  for select using (
    database_id in (
      select id from connected_databases
      where org_id in (select org_id from users where id = auth.uid())
    )
  );

-- ============================================================
-- UPDATED_AT TRIGGER
-- ============================================================
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_organizations_updated_at
  before update on organizations
  for each row execute function update_updated_at();

create trigger trg_users_updated_at
  before update on users
  for each row execute function update_updated_at();

create trigger trg_connected_databases_updated_at
  before update on connected_databases
  for each row execute function update_updated_at();

create trigger trg_alert_configs_updated_at
  before update on alert_configs
  for each row execute function update_updated_at();