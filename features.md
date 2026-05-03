# Features

SchemaZero is built for startup engineering teams that move fast and can't afford to find out from a customer that a migration broke production. It watches your database schema, scores the risk of every change, and tells the on-call engineer what to do — in plain English — within seconds.

This document lists what is actually built today.

---

## Real-time schema change detection

Scout watches every connected database continuously and captures a before/after snapshot the moment a structural change happens.

| Engine | Detection method | Latency |
|---|---|---|
| PostgreSQL (direct) | `pg_notify` on DDL event trigger, polling fallback | Sub-second |
| Supabase (direct) | `pg_notify` on DDL event trigger | Sub-second |
| Supabase (pooler / 6543) | Polling `information_schema` | Up to 30s |
| Neon | `pg_notify` + auto-reconnect on compute pause | Sub-second |
| CockroachDB | `pg_notify`, polling fallback | Sub-second |
| AWS RDS / Heroku / Railway / ElephantSQL / Timescale | `pg_notify`, polling fallback | Sub-second |
| MySQL / MariaDB / PlanetScale / Aurora MySQL | Polling `information_schema` | Up to 60s |
| MongoDB (Atlas M10+, replica sets) | Change streams | Sub-second |
| Redis (incl. Upstash, ElastiCache, Redis Cloud) | Keyspace notifications, polling fallback | Sub-second |

Scout writes a heartbeat every 30 seconds. The dashboard turns the status pill red after 90 seconds of silence so a broken connection is visible immediately.

---

## AI impact analysis

Zero analyzes every detected change and produces a plain-English summary the on-call engineer can act on without reading SQL.

- **Risk score** — LOW / MEDIUM / HIGH / CRITICAL, derived from deterministic rules then refined by Claude
- **Impact summary** — what the change affects, in one paragraph
- **Affected components** — queries, services, indexes that depend on the changed object
- **Next action** — concrete recommendation (e.g., *"Do not deploy until verified"*, *"Stop. Escalate immediately"*)

### Scoring rules

| Change | Risk |
|---|---|
| Column added (nullable), index added | LOW |
| Column type widened, constraint added, index dropped (low traffic) | MEDIUM |
| Column dropped, NOT NULL added, index dropped (critical table) | HIGH |
| Table dropped, primary key changed, foreign key dropped | CRITICAL |

---

## Alert channels

Configure any combination. Alerts fire in this order: webhook → Slack → PagerDuty → email. A failure in one channel does not block the others.

| Channel | When it fires | Setup |
|---|---|---|
| Custom webhook | Configurable threshold | Paste URL, verify HMAC-SHA256 signature on receipt |
| Slack | HIGH and CRITICAL | Slack Incoming Webhook URL, Block Kit formatted |
| PagerDuty | CRITICAL only | Events API v2 Integration Key |
| Email | Configurable threshold | Recipient list, HTML formatted |

Test alerts can be fired from Settings before saving — the team can verify routing works without waiting for a real change.

---

## Dashboard

- **Change feed** — reverse-chronological list of every detected change. New changes slide in without a page refresh. Click any card for the before/after JSON, AI impact analysis, and affected components.
- **Database list** — every connected database with engine, Scout status, and pause/resume controls. Disable monitoring without disconnecting.
- **Settings** — alert channel configuration, notify-on risk thresholds, test-send button.
- **Trial banner** — days remaining, upgrade CTA when fewer than 3 days are left.

---

## Guided onboarding

Obi is the onboarding agent. New users land on `/onboarding` after signup and are walked through connecting their first database conversationally:

1. Pick an engine (PostgreSQL, Supabase, Neon, CockroachDB, MySQL, MariaDB, MongoDB, Redis, and more)
2. Paste a connection string — Obi validates reachability before saving
3. Scout starts watching, the user is redirected to the dashboard

SSL handling, scheme normalization (`postgres://` vs `postgresql://`), and pooler detection (Supabase 6543) are automatic. A startup engineer pastes the string from their provider's dashboard and it works.

---

## Security

- **Read-only credentials** — SchemaZero requires only `SELECT` on `information_schema`. It cannot write to the customer database.
- **Schema-only** — no row data is ever read, transmitted, or stored. Only structure (table/column/index/constraint definitions).
- **Encryption at rest** — connection strings encrypted with AES-256-GCM in Supabase.
- **Signed webhooks** — every outbound webhook signed with HMAC-SHA256, includes a timestamp to prevent replay.
- **Org isolation** — Supabase row-level security; no organization can read another's events.

---

## Pricing and trial

| Plan | Price | Includes |
|---|---|---|
| Solo | $19/mo | 1 seat, 2 databases, all alert channels, 14-day free trial (no credit card) |
| Teams | $79/mo | Up to 10 seats, up to 10 databases, self-serve |
| Enterprise | Custom | Unlimited databases, VPC peering, SSO/SAML, SOC 2, dedicated SLA |

Trial expiration blocks dashboard access but preserves data and alert configuration so an upgrade resumes monitoring instantly. Billing runs through Lemon Squeezy with a customer portal for self-serve subscription management.

---

## Admin panel

A founder-only view at `/admin`, gated by the `ADMIN_EMAIL` environment variable. Customers never see it.

- **Overview** — total orgs, active trials, conversions, expired trials, active databases, 7-day and all-time event volume, qualified leads
- **Org detail** — users, alert configuration, connected databases, recent changes, recent alert log
- **Leads** — Sal (the sales agent) flags qualified Teams/Enterprise prospects from the pricing chat; full transcript and qualification context are stored here

Same panel works in managed-SaaS and self-hosted modes — the only difference is how many orgs appear.

---

## Built for the startup stack

The engines startups actually run on are first-class:

- **Supabase** — both direct (port 5432, real-time) and pooler (port 6543, polling) connection strings handled automatically
- **Neon** — auto-reconnect handles compute pauses; no missed changes
- **PlanetScale / Aurora MySQL** — polling-based detection works across managed MySQL providers
- **MongoDB Atlas** — change streams on M10+
- **Upstash Redis** — TLS (`rediss://`) handled automatically; falls back to polling when `CONFIG SET` is restricted
- **CockroachDB Cloud** — `verify-full` SSL applied automatically

Coming next: SQL Server, Snowflake, Oracle (stub listeners exist; polling-based detection planned).

---

## What SchemaZero does not do

Honest scope, so a startup team can decide if it fits:

- It does **not block** schema changes. Detection is reactive — Scout sees the change after it lands, then alerts. For Postgres, a future feature could add an event-trigger guardrail; today, the value is fast detection and a clear next action.
- It does **not** read row-level data. Schema only.
- It does **not** auto-rollback. The on-call engineer reads the alert and decides what to do.
- It does **not** require migration tooling adoption. Schema changes from any source — psql, the Supabase dashboard, an ORM auto-migration on deploy, a contractor running ad-hoc DDL — are all detected the same way.
