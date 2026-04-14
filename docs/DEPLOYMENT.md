# SchemaZero Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Variables](#environment-variables)
3. [Step-by-Step Deployment](#step-by-step-deployment)
   - [Supabase Setup](#1-supabase-setup)
   - [Railway (Backend)](#2-railway-backend)
   - [Vercel (Frontend)](#3-vercel-frontend)
4. [How to Add a New Database Engine Listener](#how-to-add-a-new-database-engine-listener)
5. [How to Modify Agent Behavior via MD Files](#how-to-modify-agent-behavior-via-md-files)
6. [How to Add a New Alert Channel](#how-to-add-a-new-alert-channel)
7. [Running Tests](#running-tests)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Node.js 20+
- Python 3.11+
- Supabase project (database + auth)
- Railway account
- Vercel account
- Anthropic API key

---

## Environment Variables

### Backend (Railway — `apps/agent/`)

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key from console.anthropic.com |
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (full access) |
| `ENCRYPTION_KEY` | Base64-encoded 32-byte AES-256 key for connection string encryption |
| `SCHEMAZERO_WEBHOOK_SIGNING_SECRET` | Shared secret for signing outbound webhook payloads |
| `SLACK_WEBHOOK_URL` | Default Slack webhook URL (orgs can override in alert_configs) |
| `PAGERDUTY_API_KEY` | PagerDuty Events API v2 key |
| `RESEND_API_KEY` | Resend API key for email alerts (or configure SMTP vars) |
| `SMTP_HOST` | SMTP server hostname (if using SMTP instead of Resend) |
| `SMTP_PORT` | SMTP server port |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `DASHBOARD_URL` | Base URL of the frontend, e.g. `https://app.schemazero.com` |
| `RAILWAY_API_URL` | Internal Railway service URL (set automatically by Railway) |

Generate a valid `ENCRYPTION_KEY`:

```bash
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

### Frontend (Vercel — `apps/web/`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (public) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key (public) |
| `NEXT_PUBLIC_LEMONSQUEEZY_STORE_ID` | Lemon Squeezy store ID |
| `RAILWAY_API_URL` | Backend URL on Railway (server-side only) |
| `LEMONSQUEEZY_API_KEY` | Lemon Squeezy API key (server-side) |
| `LEMONSQUEEZY_WEBHOOK_SECRET` | Lemon Squeezy webhook signing secret |
| `LEMONSQUEEZY_SOLO_VARIANT_ID` | Lemon Squeezy variant ID for the Solo plan |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (server-side API routes) |

---

## Step-by-Step Deployment

### 1. Supabase Setup

1. Create a new Supabase project at [supabase.com](https://supabase.com).
2. Run the base schema:
   ```bash
   psql "$SUPABASE_DB_URL" < docs/base_schema.sql
   ```
3. Run any pending migrations in order:
   ```bash
   psql "$SUPABASE_DB_URL" < supabase/migrations/001_cleanup.sql
   psql "$SUPABASE_DB_URL" < supabase/migrations/002_leads.sql
   psql "$SUPABASE_DB_URL" < supabase/migrations/003_agent_versions.sql
   psql "$SUPABASE_DB_URL" < supabase/migrations/004_lemonsqueezy.sql
   ```
4. Enable Row Level Security (RLS) on all tables — policies are defined in `supabase/schema.sql`.
5. Copy your project URL and keys from **Project Settings → API**.

### 2. Railway (Backend)

1. Install the Railway CLI:
   ```bash
   npm install -g @railway/cli
   railway login
   ```
2. Create a new Railway project and link it:
   ```bash
   cd apps/agent
   railway init
   ```
3. Set all backend environment variables:
   ```bash
   railway variables set ANTHROPIC_API_KEY=sk-ant-...
   railway variables set NEXT_PUBLIC_SUPABASE_URL=https://...
   railway variables set SUPABASE_SERVICE_ROLE_KEY=...
   railway variables set ENCRYPTION_KEY=...
   # ... set remaining variables
   ```
4. Deploy:
   ```bash
   railway up
   ```
5. Confirm the health check passes:
   ```bash
   curl https://<your-railway-url>/health
   # Expected: {"status":"ok","version":"..."}
   ```

The Railway config (`apps/agent/railway.toml`) is already set with:
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- Restart policy: `always`

### 3. Vercel (Frontend)

1. Install the Vercel CLI:
   ```bash
   npm install -g vercel
   vercel login
   ```
2. Link the project:
   ```bash
   cd apps/web
   vercel link
   ```
3. Set environment variables in the Vercel dashboard or via CLI:
   ```bash
   vercel env add NEXT_PUBLIC_SUPABASE_URL
   vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY
   vercel env add RAILWAY_API_URL
   # ... set remaining variables
   ```
4. Deploy to production:
   ```bash
   vercel --prod
   ```

The Vercel config (`apps/web/vercel.json`) is already set with:
- Framework: `nextjs`
- Build: `next build`
- Output: `.next`

---

## How to Add a New Database Engine Listener

Scout listeners live in `apps/agent/scout/listeners/`. Each listener inherits from `base_listener.py`.

**Steps:**

1. Create a new file `apps/agent/scout/listeners/<engine>_listener.py`.

2. Inherit from `BaseListener` and implement all four abstract methods:

   ```python
   from .base_listener import BaseListener

   class MyEngineListener(BaseListener):
       async def connect(self) -> None:
           # Establish connection to the database
           ...

       async def listen(self) -> None:
           # Start the listen/poll loop; write change_events to Supabase
           # Call self.update_heartbeat() every 30 seconds
           # Call self.trigger_zero(change_event_id) on each detected change
           ...

       async def capture_snapshot(self) -> dict:
           # Return a JSON-serializable dict of the current schema state
           ...

       async def disconnect(self) -> None:
           # Clean up connections
           ...
   ```

3. Register the listener in `apps/agent/scout/scout_runner.py`:

   ```python
   from listeners.myengine_listener import MyEngineListener

   ENGINE_LISTENER_MAP = {
       ...
       "myengine": MyEngineListener,
   }
   ```

4. Add the engine name to the `engine` enum in `apps/agent/models/database.py` and `supabase/schema.sql`.

5. Add the required Python driver to `apps/agent/requirements.txt`.

6. Write unit tests covering your listener's snapshot and diff logic.

---

## How to Modify Agent Behavior via MD Files

All agent behavior is defined in `/agents/*.md` files. These are loaded at runtime as system prompts — you do not need to touch any Python code to change what an agent says or does.

**Agent files:**
| File | Agent | Purpose |
|---|---|---|
| `agents/scout.md` | Scout | Background schema watcher |
| `agents/zero.md` | Zero | Impact analyzer and risk scorer |
| `agents/obi.md` | Obi | Onboarding guide |
| `agents/sal.md` | Sal | Sales qualifier |
| `agents/sully.md` | Sully | Support agent |

**To change agent behavior:**

1. Open the relevant `.md` file.
2. Edit the fallback prompt, knowledge base, or skills table.
3. Commit and push — changes take effect immediately on the next agent invocation (no redeploy needed for Railway as the MD files are read at request time).

**Key sections in each MD file:**
- **Role description** — What the agent does
- **Fallback prompt** — The system prompt sent to Claude API
- **Knowledge base** — Facts the agent knows (pricing, engines, etc.)
- **Skills table** — Enabled capabilities
- **Handoff signals** — How the agent routes to other agents
- **Settings** — `model`, `temperature`, `max_tokens`

**Do not** hardcode agent-specific logic in Python. All behavioral changes go in the MD file.

---

## How to Add a New Alert Channel

Alert channels are wired in `apps/agent/zero/alert_dispatcher.py` and implemented as services in `apps/agent/services/`.

**Steps:**

1. Create `apps/agent/services/<channel>_service.py` implementing a `send_alert()` async method:

   ```python
   class MyChannelService:
       def __init__(self, ...):
           ...

       async def send_alert(self, **kwargs) -> bool:
           # Send the alert; return True on success, False on failure
           ...
   ```

2. Add a `_fire_<channel>` method to `AlertDispatcher` in `apps/agent/zero/alert_dispatcher.py` following the pattern of existing channels.

3. Add the channel to the `dispatch()` method in the correct order. Per `zero.md`, the order is:
   - Custom webhook (always first)
   - Slack (HIGH and CRITICAL)
   - PagerDuty (CRITICAL only)
   - Email (based on org config)
   - New channel (add after email, or in the appropriate position)

4. Add any new config fields to the `alert_configs` table in Supabase and update `apps/agent/models/alert.py`.

5. Add the new channel config to the settings page in `apps/web/app/dashboard/settings/page.tsx`.

6. Write unit tests in `apps/agent/tests/test_alert_dispatcher.py`.

---

## Running Tests

```bash
cd apps/agent

# Install dependencies including test tools
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_risk_scorer.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=. --cov-report=term-missing
```

**Test files:**
| File | Covers |
|---|---|
| `tests/test_risk_scorer.py` | All risk levels, constraint and column modification edge cases |
| `tests/test_schema_diff.py` | PostgreSQL schema diff — columns, tables, indexes, constraints |
| `tests/test_alert_dispatcher.py` | Alert routing, channel isolation, fault tolerance |
| `tests/test_encryption.py` | AES-256-GCM encrypt/decrypt, wrong-key rejection, tamper detection |

---

## Troubleshooting

**Scout is not detecting changes**
- Check the Scout heartbeat in the `scout_heartbeat` table — if the `last_seen` timestamp is stale (>60s), Scout has crashed.
- View Railway logs: `railway logs`
- Verify the connection string is correct and Scout has read-only access to the database.

**Zero is not writing impact analysis**
- Check the `change_events` table — if `risk_level` is null, Zero has not processed the event.
- Verify `ANTHROPIC_API_KEY` is set correctly in Railway.
- Check Railway logs for Claude API errors.

**Alerts are not firing**
- Check the `notification_log` table — every alert attempt (success or failure) is logged there.
- Verify `alert_configs` has the correct webhook URL, Slack URL, or PagerDuty key.
- Verify `notify_on` includes the risk level you are testing with.

**Frontend build fails on Vercel**
- Check all `NEXT_PUBLIC_*` environment variables are set in the Vercel dashboard.
- Run `next build` locally to reproduce the error: `cd apps/web && npm run build`.

**Connection string encryption fails**
- The `ENCRYPTION_KEY` must be a base64-encoded 32-byte value. Generate a new one:
  ```bash
  python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
  ```
- If you rotate the key, you must re-encrypt all existing connection strings in the `connected_databases` table.
