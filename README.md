# SchemaZero

> Your database schema changed. Know what it means before it breaks production.

SchemaZero is a universal schema change detection and impact analysis platform. It watches connected databases for structural changes, analyzes what they affect, scores the risk, and tells your team exactly what to do — before anything breaks.

---

## What It Does

- Detects schema changes in real time across PostgreSQL, MySQL, MongoDB, Redis, and more
- Analyzes impact — which queries, indexes, and services are affected
- Scores risk — LOW, MEDIUM, HIGH, CRITICAL
- Fires alerts to your custom webhook, Slack, PagerDuty, or email
- Explains everything in plain English — not log output

> SchemaZero never sees your data. It only sees your structure. Read-only access only.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, Vercel |
| Backend | FastAPI (Python), Railway |
| Database + Auth | Supabase (PostgreSQL) |
| AI | Anthropic Claude API |
| Billing | Lemon Squeezy |
| Alerts | Custom webhook, Slack, PagerDuty, Email |

---

## Pricing

| Plan | Price | Details |
|---|---|---|
| Solo | $19/mo | 1 seat, 2 databases, full access, 14-day free trial |
| Teams | $79/mo | Up to 10 seats, up to 10 databases, self-serve |
| Enterprise | Custom | Unlimited databases, VPC peering, SSO/SAML, SOC 2, dedicated SLA |

Solo includes a **14-day free trial — no credit card required.**
Teams and Enterprise have no trial — contact for access.

---

## Build Phases

- [x] Phase 1 — Project scaffold
- [x] Phase 2 — Agent skill files
- [x] Phase 3 — FastAPI backend core
- [x] Phase 4 — Schema diff and impact engine
- [x] Phase 5 — Next.js frontend
- [x] Phase 6 — Auth and trial logic
- [x] Phase 7 — Alert integrations (webhook, Slack, PagerDuty, email)
- [x] Phase 8 — Scout listeners (PostgreSQL, MySQL, MongoDB, Redis)
- [x] Phase 9 — Testing and deployment config
- [x] Phase 10 — Billing, final cleanup

---

## Environment Variables

### Vercel (Frontend)

```env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
RAILWAY_API_URL=
ADMIN_EMAIL=
LEMONSQUEEZY_API_KEY=
LEMONSQUEEZY_WEBHOOK_SECRET=
LEMONSQUEEZY_SOLO_VARIANT_ID=
NEXT_PUBLIC_LEMONSQUEEZY_STORE_ID=
```

### Railway (Backend)

```env
NEXT_PUBLIC_SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
ANTHROPIC_API_KEY=
ENCRYPTION_KEY=
SCHEMAZERO_WEBHOOK_SIGNING_SECRET=
DASHBOARD_URL=
```

---

## Repository Structure

```
zero-db/
├── apps/
│   ├── web/          # Vercel frontend (Next.js 14)
│   └── agent/        # Railway backend (FastAPI)
├── packages/
│   ├── schema-diff/  # Core diff engine
│   └── impact/       # Impact analysis logic
├── agents/           # Agent skill MD files
├── docs/             # Documentation and guides
└── supabase/         # Schema and migrations
```

---

## Security

- Read-only database credentials — SchemaZero never writes to your database
- Connection strings encrypted at rest with AES-256-GCM
- Schema metadata only — no row-level data, ever
- Webhook payloads signed with HMAC-SHA256

---

## Status

🟡 In active development.
