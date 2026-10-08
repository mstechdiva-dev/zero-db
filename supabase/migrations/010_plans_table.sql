-- Migration 010: plans table (what each plan includes), and organizations.plan must point at it.
-- Safe to re-run. Only needed on a database created before this was added to supabase/schema.sql.
-- ============================================================
-- Plans: the single source of truth for what each plan includes.
-- The backend checks an org's plan against this table before it runs anything
-- for that org, and refuses to run if a plan is missing from it. Only the
-- service role can change it. Edit a limit here and it applies everywhere.
-- ============================================================
create table if not exists plans (
  name           plan_type primary key,
  display_name   text    not null,
  is_paid        boolean not null,
  max_databases  integer,   -- null = unlimited
  max_seats      integer,   -- null = unlimited
  price_cents    integer    -- null = custom pricing
);

insert into plans (name, display_name, is_paid, max_databases, max_seats, price_cents) values
  ('trial',      'Free trial', false, 2,    1,    0),
  ('solo',       'Solo',       true,  2,    1,    1900),
  ('teams',      'Teams',      true,  10,   10,   7900),
  ('enterprise', 'Enterprise', true,  null, null, null)
  on conflict (name) do nothing;

alter table plans enable row level security;
drop policy if exists "anyone_can_read_plans" on plans;
create policy "anyone_can_read_plans" on plans for select using (true);
revoke insert, update, delete on plans from anon, authenticated;


do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'organizations_plan_fkey'
  ) then
    alter table organizations
      add constraint organizations_plan_fkey foreign key (plan) references plans(name);
  end if;
end $$;
