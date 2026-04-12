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
-- ============================================================
alter type alert_channel add value if not exists 'webhook' before 'slack';

-- ============================================================
-- 3. alert_configs — add custom webhook URL column
-- ============================================================
alter table alert_configs
  add column if not exists custom_webhook_url text;

-- ============================================================
-- 4. impact_analysis — add next_action column
-- ============================================================
alter table impact_analysis
  add column if not exists next_action text;
