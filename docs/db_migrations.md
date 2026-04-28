# SchemaZero — Database Migration Log

All SQL executed against the Supabase database is tracked here.
Update this file every time a migration is run.

---

## Migration History

| # | File | Description | Status | Date |
|---|------|-------------|--------|------|
| 000 | `supabase/schema.sql` | Base schema — enums, tables, RLS policies, triggers | ✅ Completed | 2026-04-12 |
| 001 | `supabase/migrations/001_cleanup.sql` | Lemon Squeezy columns, webhook enum value, custom_webhook_url, next_action | ✅ Completed | 2026-04-12 |
| 002 | `supabase/migrations/002_waitlist.sql` | Waitlist table for landing page email capture | ⏳ Pending | — |

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

### 002 — Waitlist (`supabase/migrations/002_waitlist.sql`)
**Status:** ⏳ Pending — run this in Supabase SQL Editor before launching the landing page

```sql
create table waitlist (
  email text primary key,
  created_at timestamptz default now()
);
```

No RLS needed — the `/api/waitlist` route uses the service role key which bypasses RLS.

---

## How to Update This File

When a migration is run:
1. Add a row to the Migration History table above
2. Add a detail block at the bottom
3. Mark status as ✅ Completed with the date, or ❌ Failed / ⏳ Pending as appropriate
