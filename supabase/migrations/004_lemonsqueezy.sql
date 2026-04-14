-- Add Lemon Squeezy billing fields to organizations.
-- Replaces the placeholder Stripe columns.

ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS lemonsqueezy_customer_id    TEXT,
  ADD COLUMN IF NOT EXISTS lemonsqueezy_subscription_id TEXT,
  ADD COLUMN IF NOT EXISTS lemonsqueezy_customer_portal_url TEXT;
