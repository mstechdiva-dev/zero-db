# Features

SchemaZero is built for startup engineering teams that move fast and can't afford to find out from a customer that a migration broke production. It watches your database schema, scores the risk of every change, and tells the on-call engineer what to do — in plain English — within seconds.

The product is strongest where modern startups concentrate: the Postgres ecosystem (Postgres, Supabase, Neon, PlanetScale Postgres, CockroachDB) and MongoDB Atlas, where engines expose native DDL events and Scout gets sub-second detection. MySQL family is supported via polling.

This document lists what is actually built today.

---

## Real-time schema change detection

Scout watches every connected database continuously and captures a before/after snapshot the moment a structural change happens. Detection quality depends on what the engine exposes — the table below is honest about which engines give us sub-second events and which fall back to polling.

### Tier 1 — Real-time, native event triggers

The Postgres ecosystem. This is where SchemaZero is strongest, and it's where most modern startups land.

| Engine | Detection method | Latency |
|---|---|---|
| PostgreSQL (direct) | `pg_notify` on DDL event trigger | Sub-second |
| Supabase (direct, port 5432) | `pg_notify` on DDL event trigger | Sub-second |
| Neon | `pg_notify` + auto-reconnect on compute pause | Sub-second |
| PlanetScale Postgres (Metal) | `pg_notify` on DDL event trigger | Sub-second |
| CockroachDB Cloud | `pg_notify` | Sub-second |
| AWS RDS Postgres / Heroku / Railway / ElephantSQL / Timescale | `pg_notify` (polling fallback if event-trigger privilege is denied) | Sub-second |

### Tier 2 — Real-time, change streams

| Engine | Detection method | Latency |
|---|---|---|
| MongoDB Atlas (M10+, replica sets, sharded clusters) | Change streams on `createCollection`, `dropCollection`, `createIndexes`, `dropIndexes` | Sub-second |
| Redis (Upstash, ElastiCache, Redis Cloud) | Keyspace notifications, polling fallback when `CONFIG SET` is restricted | Sub-second |

Note: Atlas M0 (free tier) and shared M2/M5 tiers do not support change streams. Atlas customers need M10 or higher to use SchemaZero in real-time mode.

### Tier 3 — Polling

Engines that don't expose DDL events. SchemaZero polls `information_schema` on a fixed interval; changes show up within one polling cycle.

| Engine | Detection method | Latency |
|---|---|---|
| MySQL / MariaDB / PlanetScale (MySQL) / Aurora MySQL | Poll `information_schema.tables`, `columns`, `statistics` every 60s | Up to 60s |
| Supabase (PgBouncer pooler, port 6543) | Poll `information_schema` every 30s | Up to 30s |

Supabase customers using the pooler connection get polling; the direct connection (5432) gets real-time. Onboarding detects the port automatically and routes accordingly.

Scout writes a heartbeat every 30 seconds across all tiers. The dashboard turns the status pill red after 90 seconds of silence so a broken connection is visible immediately.

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

- **Minimal credentials** — SchemaZero requires only `SELECT` on `information_schema` for polling-mode databases. For real-time Postgres monitoring, it also installs DDL event triggers (requires trigger-creation privileges); for real-time Redis monitoring, it runs `CONFIG SET notify-keyspace-events` (requires CONFIG privileges or falls back to polling). No row data is written or read.
- **Schema-only** — no row data is ever read, transmitted, or stored. Only structure (table/column/index/constraint definitions).
- **Encryption at rest** — connection strings encrypted with AES-256-GCM in Supabase.
- **Signed webhooks** — every outbound webhook signed with HMAC-SHA256, includes a timestamp to prevent replay.
- **Org isolation** — Supabase row-level security; no organization can read another's events.

---

## Pricing and trial

| Plan | Price | Includes |
|---|---|---|
| Solo | $19/mo | 1 seat, 2 databases, all alert channels, 14-day free trial (no credit card) |
| Teams | $79/mo | Up to 10 seats, up to 10 databases (waitlist — not yet self-serve) |
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

Most modern startups run on the Postgres ecosystem or MongoDB Atlas — and that's where SchemaZero gives sub-second detection with zero engineering effort from the customer. Connection-string quirks that normally take an afternoon to debug are handled automatically.

**Postgres ecosystem (Tier 1 — real-time):**

- **Supabase** — direct (5432, real-time via `pg_notify`) and pooler (6543, polling) handled automatically; SSL applied to `*.supabase.co` without configuration
- **Neon** — auto-reconnect on compute pause with backoff (5s → 60s); Scout takes a fresh snapshot on reconnect so no changes are missed during sleep
- **PlanetScale Postgres (Metal)** — event triggers work natively; price ($50/mo) aligns with the SchemaZero Teams plan
- **CockroachDB Cloud** — `verify-full` SSL applied automatically for `*.cockroachlabs.cloud`
- **AWS RDS / Heroku / Railway / Timescale Cloud / ElephantSQL** — `pg_notify` where privileges allow, polling fallback otherwise

**MongoDB Atlas (Tier 2 — real-time):** Change streams on M10+ surface `createCollection`, `dropCollection`, `createIndexes`, and `dropIndexes`. Validation schema changes (`collMod`) are not yet detected.

**Redis (Tier 2 — real-time):** Upstash, ElastiCache, and Redis Cloud all work. TLS (`rediss://`) handled automatically; keyspace notifications enabled on connect; polling fallback when the provider blocks `CONFIG SET`.

**MySQL family (Tier 3 — polling):** PlanetScale (MySQL), Aurora MySQL, RDS MySQL, and MariaDB are detected via 60-second polling. Honest tradeoff: detection latency is up to one minute, not sub-second.

**Pricing alignment with the customer's stack:** Solo ($19/mo) lines up with the typical solo-founder bill (Supabase Pro $25, Neon Launch $5+, Cloudflare D1 $5). Teams ($79/mo) lines up with the team-of-engineers bill (MongoDB M10 $57, PlanetScale Postgres Metal $50).

### On the roadmap

| Engine | Status | Why it's not Tier 1 |
|---|---|---|
| SQL Server | Stub listener exists; polling planned | Has DDL triggers, but small startup footprint |
| Snowflake | Stub listener exists; polling planned | OLTP-secondary; analytics workload |
| Oracle | Stub listener exists; polling planned | Rare in startups |
| Aurora DSQL | Verifying event-trigger support | Postgres-compatible but excludes some extensions; needs a spike before listing as supported |
| Cloudflare D1 / Turso (libSQL) | Not started | SQLite — no DDL events; would share a polling adapter |
| DynamoDB | Not started | Would poll CloudTrail `CreateTable` / `UpdateTable` events |
| Convex | Not started | Schema-as-code deployed via CLI; git/deploy hook is the natural detection path, not the DB |

---

## What SchemaZero does not do

Honest scope, so a startup team can decide if it fits:

- It does **not block** schema changes. Detection is reactive — Scout sees the change after it lands, then alerts. For Postgres, a future feature could add an event-trigger guardrail; today, the value is fast detection and a clear next action.
- It does **not** read row-level data. Schema only.
- It does **not** auto-rollback. The on-call engineer reads the alert and decides what to do.
- It does **not** require migration tooling adoption. Schema changes from any source — psql, the Supabase dashboard, an ORM auto-migration on deploy, a contractor running ad-hoc DDL — are all detected the same way.
