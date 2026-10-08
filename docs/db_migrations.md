# SchemaZero — Database Migration Log

All SQL executed against the Supabase database is tracked here.
Update this file every time a migration is run.

---

> **Schema consolidated (2026-10-08).** `supabase/schema.sql` is now the complete schema and already includes everything migrations 001 to 007 add, plus fixes found by checking the code against a real Postgres (live updates for the change feed, permission to pause and delete databases from the dashboard, no browser access to saved connection strings). A new or reset database needs only that one file. `supabase/reset.sql` clears an old or mismatched schema first. The migrations below are history for databases built from the earlier `schema.sql`; keep them only for reference.

## Migration History

| # | File | Description | Status | Date |
|---|------|-------------|--------|------|
| 000 | `supabase/schema.sql` | Base schema — enums, tables, RLS policies, triggers | ✅ Completed | 2026-04-12 |
| 001 | `supabase/migrations/001_cleanup.sql` | Lemon Squeezy columns, webhook enum value, custom_webhook_url, next_action | ✅ Completed | 2026-04-12 |
| 002 | `supabase/migrations/002_leads.sql` | Sales leads table (admin panel) | Check | — |
| 003 | `supabase/migrations/003_agent_versions.sql` | Saved agent edits (admin panel) | Check | — |
| 004 | `supabase/migrations/004_lemonsqueezy.sql` | Lemon Squeezy customer portal column | Check | — |
| 005 | `supabase/migrations/005_waitlist.sql` | Waitlist table for landing page email capture | ⏳ Pending | — |
| 006 | `supabase/migrations/006_change_types.sql` | `change_type` values Scout writes (`table_created`, `index_created`, `key_type_changed`, `ttl_policy_changed`) | ⏳ Pending | — |
| 007 | `supabase/migrations/007_stripe.sql` | Billing columns renamed to `stripe_*`, Lemon Squeezy portal column dropped | ⏳ Pending | — |
| 008 | `supabase/migrations/008_mongo_change_types.sql` | `collection_created` and `schema_change` change types (MongoDB listener) | ⏳ Pending if you ran `schema.sql` before it was added | — |

---

## Migration Details

### 000 — Base Schema (`supabase/schema.sql`)
**Status:** ✅ Completed — 2026-04-12

Initial database setup. Creates:
- Extensions: `uuid-ossp`, `pgcrypto`
- Enums: `plan_type`, `user_role`, `db_engine`, `change_type`, `risk_level`, `alert_channel`, `notification_status`
- Tables: `organizations`, `users`, `connected_databases`, `scout_heartbeat`, `change_events`, `impact_analysis`, `alert_configs`, `notification_log`
- RLS policies on all tables
- Trigger: `set_updated_at` on `alert_configs`
- Trigger: `handle_new_user` on `auth.users` — provisions org + user + alert_config on signup

---

### 001 — Cleanup (`supabase/migrations/001_cleanup.sql`)
**Status:** ✅ Completed — 2026-04-12

Applies build.md updates to the existing schema:
- `organizations.stripe_customer_id` → `lemonsqueezy_customer_id`
- `organizations.stripe_subscription_id` → `lemonsqueezy_subscription_id`
- `alert_channel` enum: added `webhook` before `slack`
- `alert_configs`: added `custom_webhook_url text`
- `impact_analysis`: added `next_action text`

---

### 005 — Waitlist (`supabase/migrations/005_waitlist.sql`)
**Status:** ⏳ Pending. Run in the Supabase SQL Editor before launching the landing page.

Creates `waitlist (id, email unique, created_at)` with row-level security on and no policies. The `/api/waitlist` route uses the service role key, which bypasses it. If you already created a `waitlist` table with `email` as the key, this is skipped safely.

---

### 006 — Change types (`supabase/migrations/006_change_types.sql`)
**Status:** ⏳ Pending. Run before connecting databases.

Adds `table_created`, `index_created`, `key_type_changed` and `ttl_policy_changed` to the `change_type` enum. Scout writes these names, and the database rejected them before, so those events were lost. Safe to run again.

---

### 007 — Stripe billing (`supabase/migrations/007_stripe.sql`)
**Status:** ⏳ Pending. Run before taking payments.

Billing moved from Lemon Squeezy to Stripe. Renames `organizations.lemonsqueezy_customer_id` and `lemonsqueezy_subscription_id` to `stripe_customer_id` and `stripe_subscription_id` (existing values are kept) and drops `lemonsqueezy_customer_portal_url`, since Stripe creates portal links on demand. Safe to run again.

---

### 008 — MongoDB change types (`supabase/migrations/008_mongo_change_types.sql`)
**Status:** Run it if your database was created from an earlier `schema.sql`.

Adds `collection_created` (MongoDB `createCollection`) and `schema_change` (anything the listener doesn't recognise). Both were missing, so those events were rejected by the database and lost. The current `schema.sql` already includes them. Safe to run again.

---

## How to Update This File

When a migration is run:
1. Add a row to the Migration History table above
2. Add a detail block at the bottom
3. Mark status as ✅ Completed with the date, or ❌ Failed / ⏳ Pending as appropriate
