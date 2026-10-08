-- Migration 005: Waitlist
-- Used by POST /api/waitlist (landing page "Join waitlist" form).
-- Written with the service role key; RLS on with no policies keeps it private.

create table if not exists waitlist (
  id         uuid primary key default gen_random_uuid(),
  email      text not null unique,
  created_at timestamptz not null default now()
);

alter table waitlist enable row level security;
