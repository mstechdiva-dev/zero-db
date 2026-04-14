# Changelog

## v0.1.0 — 2026-04-14

Initial build. Full stack from scaffold to billing.

### Added

**Infrastructure**
- Next.js 14 frontend on Vercel
- FastAPI backend on Railway
- Supabase for database, auth, and real-time subscriptions
- Monorepo structure: `apps/web`, `apps/agent`, `packages/`

**Agent Skill System**
- Agent behavior defined in `/agents/*.md` files — editable without code changes
- Five agents: background watcher, impact analyzer, onboarding guide, sales qualifier, support
- Admin panel editor at `/admin/agents` — edit live prompts, changes take effect immediately
- Agent content stored in Supabase `agent_skills` table; FastAPI reads Supabase on each call with disk fallback

**Schema Watcher (Scout)**
- PostgreSQL: pg_notify listener + polling fallback
- MySQL / MariaDB: information_schema polling every 60s
- MongoDB: change streams on admin database
- Redis: keyspace notification monitoring + SCAN polling
- SQL Server, Snowflake, Oracle: stubs (coming soon)
- Heartbeat written to `scout_heartbeat` every 30 seconds

**Schema Diff Engine**
- Before/after JSON snapshot comparison
- Detects: column add/drop/modify, table create/drop, index create/drop, constraint add/drop
- Engines: PostgreSQL, MySQL, MongoDB, Redis
- All results serializable to Supabase `change_events`

**Impact Analysis (Zero)**
- Claude API analyzes each change event
- Produces: affected queries, services, indexes, plain-English summary, next action
- Risk scoring: LOW / MEDIUM / HIGH / CRITICAL
- Next action framing: safe to deploy / review before deploying / do not deploy / stop and escalate

**Alert Channels**
- Custom webhook (always first) — HMAC-SHA256 signed payloads
- Slack — Block Kit formatted, HIGH and CRITICAL only
- PagerDuty — Events API v2, CRITICAL only
- Email — HTML template, per-org recipient list
- All attempts logged to `notification_log`

**Frontend**
- Landing page: hero, live demo, how it works, security, pricing tabs
- Auth: Supabase signup/login, org provisioning on signup
- Onboarding: agent-guided database connection flow
- Dashboard: real-time change feed, risk badges, Scout status
- Settings: alert config + billing section

**Auth and Trial**
- 14-day free trial on Solo, no credit card required
- Trial enforcement in middleware — expired trial redirects to pricing
- Trial banner with days remaining

**Billing**
- Lemon Squeezy integration
- Solo plan: $19/mo, 2 databases, 1 seat — self-serve checkout
- Teams plan: $79/mo, 10 databases, 10 seats — self-serve
- Enterprise: custom pricing, contact only
- Webhook handler: `order_created` activates plan, `subscription_cancelled` reverts to trial
- Billing section in settings: current plan, upgrade CTA for trial users, manage subscription for Solo

**Admin Panel**
- `/admin` — org overview, stats, all organizations
- `/admin/leads` — qualified sales leads from agent conversations
- `/admin/agents` — live agent skill editor with diff view

**Testing**
- pytest suite: risk scorer, schema diff, alert dispatcher, encryption
- GitHub Actions: CI runs tests + build on push to main, deploys to Railway and Vercel

**Deployment**
- `railway.toml` — build, start, health check, restart policy
- `vercel.json` — Next.js config
- `docs/DEPLOYMENT.md` — full deployment and operations guide

### Plans

| Plan | Price | Limits |
|---|---|---|
| Solo | $19/mo | 1 seat, 2 databases |
| Teams | $79/mo | 10 seats, 10 databases |
| Enterprise | Custom | Unlimited |
