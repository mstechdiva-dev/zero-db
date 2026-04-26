-- Migration 001: Cleanup
-- Applies changes from build.md updates to an existing schema installation.
-- Run this in your Supabase SQL editor.

-- ============================================================
-- 1. Organizations — swap Stripe for Lemon Squeezy
-- ============================================================
alter table organizations
  rename column stripe_customer_id to lemonsqueezy_customer_id;

alter table organizations
  rename column stripe_subscription_id to lemonsqueezy_subscription_id;

-- ============================================================
-- 2. alert_channel enum — add webhook as first-class channel
--    Creates the type if it doesn't exist, otherwise adds the value
-- ============================================================
do $$
begin
  if not exists (select 1 from pg_type where typname = 'alert_channel') then
    create type alert_channel as enum ('webhook', 'slack', 'pagerduty', 'email');
  elsif not exists (
    select 1 from pg_enum e
    join pg_type t on e.enumtypid = t.oid
    where t.typname = 'alert_channel' and e.enumlabel = 'webhook'
  ) then
    alter type alert_channel add value 'webhook' before 'slack';
  end if;
end $$;

-- ============================================================
-- 3. alert_configs — add webhook URL column
-- ============================================================
alter table alert_configs
  add column if not exists webhook_url text;

-- ============================================================
-- 4. impact_analysis — add next_action column
-- ============================================================
alter table impact_analysis
  add column if not exists next_action text;
