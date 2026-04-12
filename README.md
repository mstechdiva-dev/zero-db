# SchemaZero

> Your Postgres schema changed. Know what it means before it breaks.

SchemaZero is a schema change detection and impact analysis agent for PostgreSQL. It watches every migration, explains what changed, traces what's affected, and notifies your team — before anything breaks in production.

---

## What It Does

- Detects schema changes in real time via Supabase pg_notify
- Analyzes impact — which queries, indexes, and services are affected
- Scores risk — low, medium, or high
- Posts a detailed comment on the GitHub PR that triggered the migration
- Fires Slack and PagerDuty alerts for high risk changes
- Blocks deploys automatically when risk is critical

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vercel (Next.js) |
| Backend / Agent Engine | Railway |
| Database + Auth | Supabase (PostgreSQL) |
| Schema Watcher | Supabase pg_notify |
| GitHub Integration | GitHub App |
| Billing | Stripe |
| Alerts | Slack, PagerDuty |

---

## Agents

| Agent | Role | Runs On |
|-------|------|---------|
| Scout | Background schema watcher | Railway (always-on) |
| Zero | Impact analyzer, PR commenter, alert sender | Railway |
| Shawn | Onboarding — database connection wizard | Vercel / Supabase Edge |
| Taylor | Landing page + in-app support | Vercel |
| Jordan | Sales qualifier for Teams and Enterprise | Vercel |

---

## Pricing

| Plan | Price | Details |
|------|-------|---------|
| Solo | $19/mo | 1 seat, 1 database, full access |
| Teams | Custom | Multiple seats, multiple databases |
| Enterprise | Custom | VPC peering, SSO/SAML, SOC 2, dedicated SLA |

All plans start with a **14-day free trial. No credit card required.**

---

## Build Phases

### Phase 1 — Foundation
- [ ] Supabase project setup — auth, database schema
- [ ] Railway project setup — backend service
- [ ] GitHub App registration — webhooks, permissions
- [ ] Vercel deployment — frontend connected to repo

### Phase 2 — Agent Brain
- [ ] `schemazero-agent.md` — Zero's system prompt
- [ ] `scout-agent.md` — Scout's watcher instructions
- [ ] `onboarding-agent.md` — database connection wizard
- [ ] `taylor-agent.md` — support agent
- [ ] `jordan-agent.md` — sales qualifier

### Phase 3 — Core Engine
- [ ] Schema diff engine — before/after DDL snapshots
- [ ] pg_notify listener — Scout watching for migrations
- [ ] Impact analysis logic — traces affected queries, indexes, services
- [ ] Risk scorer — low / medium / high
- [ ] PR comment formatter — Zero's GitHub output
- [ ] Slack alert formatter — high risk notifications

### Phase 4 — Frontend
- [ ] Dashboard — live change feed, risk indicators
- [ ] Onboarding flow — database connection wizard
- [ ] Settings page — alerts, integrations, team management

### Phase 5 — Integrations
- [ ] Slack webhook
- [ ] PagerDuty
- [ ] GitHub PR comment posting
- [ ] Deploy blocking — draft PR on high risk

### Phase 6 — Auth and Billing
- [ ] Supabase auth — signup, login, session management
- [ ] Stripe — Solo $19/mo, Teams and Enterprise custom
- [ ] Trial logic — 14 days, no credit card, convert or out

---

## Environment Variables

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Railway
RAILWAY_API_URL=

# GitHub App
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=

# Alerts
SLACK_WEBHOOK_URL=
PAGERDUTY_API_KEY=

# AI
ANTHROPIC_API_KEY=
```

---

## Repository Structure

```
schemazero/
├── apps/
│   ├── web/          # Vercel frontend (Next.js)
│   └── agent/        # Railway backend (Scout + Zero)
├── packages/
│   ├── schema-diff/  # Core diff engine
│   ├── impact/       # Impact analysis logic
│   └── agents/       # Agent MD files and prompts
├── docs/
│   ├── schemazero-agent.md
│   ├── scout-agent.md
│   ├── onboarding-agent.md
│   ├── taylor-agent.md
│   └── jordan-agent.md
└── README.md
```

---

## Security

- Read-only database credentials only — SchemaZero never writes to your database
- Credentials encrypted at rest with AES-256
- Schema metadata only — no row-level data, ever
- SOC 2 Type II audit in progress
- VPC peering available on Enterprise

> **SchemaZero never sees your data. It only sees your structure.**

---

## Status

🟡 In active development — not yet publicly available.

Early access waitlist open at [schemazero.com](#)

---

## Contact

Questions: hello@schemazero.com
