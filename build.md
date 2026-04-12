# SchemaZero — Claude Code Build Guide

> This file contains phased prompts for Claude Code to build SchemaZero from start to finish.
> Each phase is a self-contained prompt. Complete each phase fully before moving to the next.
> This file is removed from the repo when the build is complete.

---

## How To Use This File

1. Open Claude Code in your terminal
2. Copy the prompt for the current phase
3. Paste it into Claude Code and let it build
4. Verify the phase is complete before moving on
5. Check off each phase as done

---

## Stack Reference

- **Frontend** — Next.js 14, deployed on Vercel
- **Backend** — FastAPI (Python), deployed on Railway
- **Database + Auth** — Supabase (PostgreSQL)
- **AI** — Anthropic Claude via API
- **Billing** — Lemon Squeezy
- **Alerts** — Custom Webhook, Slack, PagerDuty, Email

## Architecture Reference

- Agent skills live in `/agents/*.md` files — modify behavior without touching code
- Core logic lives in `/apps/agent/` — FastAPI backend
- Frontend lives in `/apps/web/` — Next.js
- Schema diff and impact logic lives in `/packages/`

---

## Phase 1 — Project Scaffold

```
You are building SchemaZero, a universal database schema change detection and impact analysis platform.

Create the full monorepo project structure for SchemaZero with the following layout:

schemazero/
├── apps/
│   ├── web/                    # Next.js 14 frontend for Vercel
│   └── agent/                  # FastAPI backend for Railway
├── packages/
│   ├── schema-diff/            # Core schema diff engine (Python)
│   └── impact/                 # Impact analysis logic (Python)
├── agents/                     # Agent MD skill files
│   ├── scout.md
│   ├── zero.md
│   ├── shawn.md
│   ├── taylor.md
│   └── jordan.md
├── supabase/
│   └── schema.sql              # Already exists - do not overwrite
├── docs/                       # Project documentation
├── build.md                    # This file - remove after build
└── README.md                   # Already exists - do not overwrite

Setup requirements:
- Initialize Next.js 14 app in apps/web with TypeScript, Tailwind CSS, App Router
- Initialize FastAPI app in apps/agent with Python 3.11+
- Create requirements.txt for FastAPI app with: fastapi, uvicorn, anthropic, supabase, asyncpg, psycopg2-binary, python-dotenv, pydantic, httpx, cryptography
- Create package.json at root for monorepo management
- Create .env.example at root with all required environment variables
- Create .gitignore that excludes .env files, __pycache__, node_modules, .next
- Create Procfile in apps/agent for Railway: web: uvicorn main:app --host 0.0.0.0 --port $PORT
- Create vercel.json in apps/web pointing to the Next.js app
- Create railway.toml in apps/agent for Railway deployment config

Environment variables needed in .env.example:
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
RAILWAY_API_URL=
LEMONSQUEEZY_API_KEY=
LEMONSQUEEZY_WEBHOOK_SECRET=
NEXT_PUBLIC_LEMONSQUEEZY_STORE_ID=
SLACK_WEBHOOK_URL=
PAGERDUTY_API_KEY=
ANTHROPIC_API_KEY=

Do not create placeholder content. Every file should be production-ready and functional.
```

---

## Phase 2 — Agent MD Skill Files

```
You are building the agent skill files for SchemaZero. These MD files define agent behavior and are loaded at runtime by the FastAPI backend. Modifying these files changes agent behavior without touching any Python code.

Each agent file must follow this exact structure based on the AgentPark/PRKitchen pattern:
- Role description
- Fallback prompt (the system prompt loaded into Claude API)
- Knowledge base (what the agent knows)
- Skills table (enabled capabilities)
- Handoff signals (how it routes to other agents)
- Settings (model, temperature, max tokens)

Create the following agent files in /agents/:

---

FILE: agents/scout.md

Scout is a background watcher agent. It runs continuously on Railway and monitors connected databases for schema changes. It does not have conversations — it detects, captures, and triggers Zero.

Scout must:
- Connect to any supported database engine using the connection string from Supabase connected_databases table
- Listen for schema changes using the appropriate method per engine:
  - PostgreSQL / Supabase / Neon / CockroachDB: pg_notify on DDL events
  - MySQL / MariaDB: polling information_schema every 60 seconds
  - MongoDB: change streams on system.namespaces
  - Redis: keyspace notifications for key pattern changes
  - SQL Server: polling sys.objects (coming soon)
  - Snowflake: polling INFORMATION_SCHEMA.TABLES (coming soon)
  - Oracle: polling ALL_OBJECTS (coming soon)
- Capture before and after state as JSON snapshots
- Write change events to Supabase change_events table
- Update scout_heartbeat table every 30 seconds
- Trigger Zero when a change event is written
- Never write to the customer database — read only

Skills table must include:
- pg_notify_listener
- polling_listener
- change_stream_listener
- snapshot_capture
- change_event_writer
- heartbeat_updater
- zero_trigger

---

FILE: agents/zero.md

Zero is the impact analyzer and decision advisor. It is triggered by Scout when a schema change is detected. It reads the change event, analyzes impact, determines the next action, scores risk, writes results to Supabase, and fires alerts.

Zero must:
- Read change events from Supabase change_events table
- Use Claude API to analyze: what changed, what it affects, what the risk is, and what the team should do next
- Write impact analysis to Supabase impact_analysis table
- Update risk_level on the change event
- Always include a next_action in plain English — not just what happened but what the team should do:
  - LOW: "Safe to deploy. No action required."
  - MEDIUM: "Review [specific thing] before deploying."
  - HIGH: "Do not deploy until this is resolved. [specific action needed]."
  - CRITICAL: "Stop. Escalate immediately. [specific action needed]."
- Fire custom webhook alert if configured (always check webhook first)
- Fire Slack alert if risk is high or critical
- Fire PagerDuty alert if risk is critical
- Send email notification based on org alert config
- Write to notification_log table for every alert sent
- Explain everything in plain English — no jargon, no log entries, no technical output without context

Risk scoring rules:
- LOW: additive changes, nullable columns added, index added
- MEDIUM: column type widened, index dropped on low-traffic table, constraint added
- HIGH: column dropped, index dropped on critical table, NOT NULL added to existing column
- CRITICAL: table dropped, primary key changed, foreign key constraint dropped

Skills table must include:
- change_event_reader
- impact_analyzer
- risk_scorer
- next_action_advisor
- webhook_alerter
- slack_alerter
- pagerduty_alerter
- email_alerter
- notification_logger
- plain_english_explainer

---

FILE: agents/shawn.md

Shawn is the onboarding agent. It guides new users through connecting their first database. It lives in the frontend onboarding flow and communicates via the FastAPI backend.

Shawn must:
- Welcome the user and explain what SchemaZero does in one sentence
- Ask for the database engine type
- Ask for the connection string
- Validate the connection is reachable (read-only test)
- Confirm what Scout will watch for this engine
- Confirm the connection is saved and Scout is now watching
- Hand off to Taylor if the user has support questions
- Hand off to Sal if the user asks about upgrading

Handoff signals:
- HANDOFF: support — route to Taylor
- HANDOFF: sales — route to Sal

Skills table must include:
- engine_selection_guide
- connection_string_validator
- read_only_connection_test
- scout_activation_confirmation
- support_handoff
- sales_handoff

Settings:
- Model: claude-haiku-4-5-20251001
- Temperature: 0.5
- Max tokens: 1024

---

FILE: agents/taylor.md

Taylor is the support agent. It lives on the landing page and in-app. It answers questions about SchemaZero, troubleshoots issues, and routes when needed.

Taylor must:
- Answer questions about how SchemaZero works
- Explain supported database engines
- Help users understand change events and risk levels
- Help users configure Slack and PagerDuty alerts
- Explain pricing and trial details
- Hand off to Sal for upgrade or enterprise questions
- Create a support ticket if the issue needs founder attention: CREATE_TICKET
- Stay strictly on SchemaZero topics — redirect off-topic questions

Handoff signals:
- HANDOFF: sales — route to Sal
- CREATE_TICKET — escalate to founder

Pricing Taylor knows:
- Solo: $19/mo, 1 seat, 1 database, full access, 14-day free trial, no credit card required
- Teams: Custom pricing, talk to us, no self-serve trial
- Enterprise: Custom pricing, talk to us, no self-serve trial

Skills table must include:
- product_qa
- engine_explainer
- risk_level_explainer
- alert_config_guide
- pricing_guide
- trial_explainer
- sales_handoff
- ticket_creation
- topic_guardrail

Settings:
- Model: claude-haiku-4-5-20251001
- Temperature: 0.7
- Max tokens: 1024

---

FILE: agents/jordan.md

Jordan is the sales qualifier agent. It handles inbound interest in Teams and Enterprise plans. It qualifies leads, collects context, and routes warm leads to the founder.

Jordan must:
- Identify buying signals — team size, urgency, database count, compliance needs
- Map prospects to the right plan — Teams or Enterprise
- Collect: company name, team size, number of databases, use case, urgency
- Flag high-priority leads: CREATE_LEAD with full context
- Never quote a price for Teams or Enterprise — always "talk to us"
- Hand off to Taylor if the question is support related

Handoff signals:
- CREATE_LEAD — send qualified lead to founder with full context
- HANDOFF: support — route to Taylor

Skills table must include:
- buying_signal_detection
- plan_mapping
- lead_qualification
- lead_creation
- support_handoff
- urgency_detection

Settings:
- Model: claude-sonnet-4-6
- Temperature: 0.6
- Max tokens: 2048

Make every agent file production-ready. These are loaded directly into the Claude API as system prompts.
```

---

## Phase 3 — FastAPI Backend Core

```
You are building the FastAPI backend for SchemaZero. This runs on Railway and is the engine that powers Scout, Zero, and the customer-facing agent APIs.

Build the complete FastAPI application in apps/agent/ with the following structure:

apps/agent/
├── main.py                     # FastAPI app entry point
├── requirements.txt
├── Procfile
├── routers/
│   ├── agent.py                # Agent chat endpoints (Shawn, Taylor, Jordan)
│   ├── databases.py            # Connected database CRUD
│   ├── changes.py              # Change events and impact analysis
│   ├── alerts.py               # Alert config endpoints
│   └── health.py               # Health check endpoint
├── services/
│   ├── anthropic_service.py    # Claude API wrapper
│   ├── supabase_service.py     # Supabase client and queries
│   ├── encryption_service.py   # AES-256 connection string encryption
│   ├── webhook_service.py      # Custom webhook sender (checked first before other alerts)
│   ├── slack_service.py        # Slack webhook sender
│   ├── pagerduty_service.py    # PagerDuty API sender
│   └── email_service.py        # Email notification sender
├── scout/
│   ├── scout_runner.py         # Main Scout orchestrator
│   ├── listeners/
│   │   ├── postgres_listener.py
│   │   ├── mysql_listener.py
│   │   ├── mongodb_listener.py
│   │   ├── redis_listener.py
│   │   └── base_listener.py    # Abstract base class all listeners inherit
│   └── snapshot.py             # Schema snapshot capture
├── zero/
│   ├── zero_runner.py          # Main Zero orchestrator
│   ├── impact_analyzer.py      # Impact analysis using Claude API
│   ├── risk_scorer.py          # Risk scoring logic
│   └── alert_dispatcher.py     # Routes alerts to correct channel
└── models/
    ├── database.py             # Pydantic models for connected databases
    ├── change_event.py         # Pydantic models for change events
    └── alert.py                # Pydantic models for alert configs

Key requirements:

1. main.py must:
   - Start FastAPI app
   - Start Scout runner as a background task on startup
   - Include all routers
   - Handle CORS for Vercel frontend
   - Load agent MD files from /agents/ directory at startup

2. anthropic_service.py must:
   - Load the correct agent MD file based on agent name
   - Call Claude API with the MD file as system prompt
   - Support streaming responses
   - Handle conversation history for multi-turn chats
   - Use model from agent settings in MD file

3. encryption_service.py must:
   - Encrypt connection strings with AES-256 before storing in Supabase
   - Decrypt connection strings when Scout needs to connect
   - Never log decrypted connection strings

4. base_listener.py must define:
   - Abstract connect() method
   - Abstract listen() method  
   - Abstract capture_snapshot() method
   - Abstract disconnect() method
   - Shared heartbeat update logic

5. postgres_listener.py must:
   - Use asyncpg for async PostgreSQL connection
   - Listen on DDL events via pg_notify
   - Capture information_schema snapshot before and after
   - Write to Supabase change_events table

6. risk_scorer.py must implement exact rules from zero.md:
   - LOW: additive changes
   - MEDIUM: widening changes
   - HIGH: destructive changes
   - CRITICAL: table drops, PK changes

7. All endpoints must:
   - Require Supabase JWT authentication
   - Return consistent JSON responses
   - Handle errors gracefully with meaningful messages

8. Agent endpoints (routers/agent.py) must:
   - Accept: agent name, message, conversation history
   - Load correct MD file
   - Call Claude API
   - Return response + any handoff signals detected
   - Support: shawn, taylor, jordan

Build every file completely. No placeholders. Production-ready Python.
```

---

## Phase 4 — Schema Diff and Impact Engine

```
You are building the core schema diff engine and impact analysis packages for SchemaZero.

Build the following in packages/:

packages/schema-diff/
├── __init__.py
├── differ.py                   # Main diff orchestrator
├── engines/
│   ├── postgres_diff.py        # PostgreSQL schema differ
│   ├── mysql_diff.py           # MySQL schema differ
│   ├── mongodb_diff.py         # MongoDB schema differ
│   ├── redis_diff.py           # Redis key pattern differ
│   └── base_diff.py            # Abstract base differ
└── models.py                   # Pydantic models for diff results

packages/impact/
├── __init__.py
├── analyzer.py                 # Main impact analyzer
├── query_tracer.py             # Finds queries affected by change
├── index_tracer.py             # Finds indexes affected by change
└── models.py                   # Pydantic models for impact results

Key requirements:

1. base_diff.py must define:
   - Abstract diff(before: dict, after: dict) method
   - Returns standardized DiffResult with:
     - change_type (matches change_events.change_type enum)
     - object_type
     - object_name
     - schema_name
     - before_state
     - after_state
     - human_readable_summary

2. postgres_diff.py must detect:
   - Column added / dropped / modified
   - Table added / dropped
   - Index added / dropped
   - Constraint added / dropped
   - Type changes
   - Nullable changes
   - Default value changes

3. mongodb_diff.py must detect:
   - Collection added / dropped
   - Index added / dropped
   - Validation schema changes

4. redis_diff.py must detect:
   - New key patterns (namespace level, not individual keys)
   - Dropped key patterns
   - TTL policy changes
   - Data type changes at pattern level

5. analyzer.py must:
   - Accept a DiffResult
   - Use Claude API via anthropic_service to analyze impact
   - Load zero.md as the system prompt for this analysis
   - Return ImpactResult with:
     - affected_queries (list)
     - affected_services (list)
     - affected_indexes (list)
     - summary (plain English — what changed and what it touches)
     - next_action (plain English — what the team should do: safe to deploy / review X before deploying / do not deploy / stop and escalate)
     - recommendations (list)

6. All diff results must be:
   - Serializable to JSON for Supabase storage
   - Human readable in summary field
   - Consistent across all database engines

Build every file completely. No placeholders.
```

---

## Phase 5 — Next.js Frontend

```
You are building the Next.js 14 frontend for SchemaZero. This is deployed on Vercel.

The landing page HTML already exists and should be used as the design reference. Recreate it faithfully in Next.js using the same colors, fonts, and layout.

Design reference:
- Background: #0a0a0a
- Accent green: #00e87a
- Font: DM Sans (body), Space Mono (code/mono elements)
- Dark theme throughout
- Tabbed navigation: Live Demo, How it works, Security, Pricing

Build the complete frontend in apps/web/ with the following structure:

apps/web/
├── app/
│   ├── layout.tsx              # Root layout with fonts and metadata
│   ├── page.tsx                # Landing page (tabbed: Demo, How it works, Security, Pricing)
│   ├── auth/
│   │   ├── login/page.tsx      # Login page
│   │   └── signup/page.tsx     # Signup - starts 14 day trial
│   ├── onboarding/
│   │   └── page.tsx            # Obi onboarding flow - connect first database
│   ├── dashboard/
│   │   ├── page.tsx            # Main dashboard - live change feed
│   │   ├── databases/page.tsx  # Connected databases management
│   │   ├── settings/page.tsx   # Alert configs, team, billing
│   │   └── layout.tsx          # Dashboard layout with sidebar nav
│   └── api/
│       ├── agent/route.ts      # Proxy to Railway agent endpoint
│       └── webhook/
│           └── lemonsqueezy/route.ts # Lemon Squeezy webhook handler
├── components/
│   ├── landing/
│   │   ├── Hero.tsx            # Hero + live demo panel
│   │   ├── HowItWorks.tsx      # How it works tab
│   │   ├── Security.tsx        # Security tab
│   │   ├── Pricing.tsx         # Pricing tab - Solo $19, Teams custom, Enterprise custom
│   │   └── Nav.tsx             # Tabbed navigation
│   ├── dashboard/
│   │   ├── ChangeCard.tsx      # Individual change event card with risk badge
│   │   ├── ChangeFeed.tsx      # Live feed of change events
│   │   ├── RiskBadge.tsx       # LOW / MEDIUM / HIGH / CRITICAL badge
│   │   ├── DatabaseCard.tsx    # Connected database status card
│   │   ├── ScoutStatus.tsx     # Scout heartbeat indicator
│   │   └── Sidebar.tsx         # Dashboard navigation sidebar
│   ├── onboarding/
│   │   ├── ChatWindow.tsx      # Obi agent chat interface
│   │   └── EngineSelector.tsx  # Database engine picker
│   └── shared/
│       ├── AgentChat.tsx       # Reusable agent chat component (Taylor, Sal, Obi)
│       └── TrialBanner.tsx     # Days remaining in trial banner
├── lib/
│   ├── supabase.ts             # Supabase client
│   ├── railway.ts              # Railway API client
│   └── lemonsqueezy.ts         # Lemon Squeezy client
└── middleware.ts               # Auth protection for dashboard routes

Key requirements:

1. Landing page (page.tsx) must:
   - Match the existing HTML design exactly
   - Tabs: Live Demo, How it works, Security, Pricing
   - Live Demo tab shows the mock change feed cards (ADDED, MODIFIED, DROPPED) — each card must show "What to review" not just "Impact", and HIGH/CRITICAL cards must show a clear next action (e.g. "Do not deploy until this is resolved")
   - Pricing tab shows: 14-day free trial on Solo only (no credit card), Solo $19/mo, Teams custom, Enterprise custom
   - Hero headline: "Stop investigating. Start knowing."
   - Hero sub: "When your schema changes, SchemaZero tells your team exactly what it affects, why it matters, and what to review — before it becomes a production incident."
   - Hero includes: "SchemaZero never sees your data. It only sees your structure."
   - Notification channels line: "Alerts land in your own custom webhook, Slack, PagerDuty, or email — where your team already works."
   - CTA buttons link to /auth/signup

2. Dashboard (dashboard/page.tsx) must:
   - Show live change feed from Supabase (real-time subscription)
   - Each change card shows: engine type, table/collection name, change type, risk level, time
   - Click a card to see full impact analysis
   - Show Scout status per connected database
   - Show trial days remaining if on trial

3. Onboarding (onboarding/page.tsx) must:
   - Show Obi agent chat interface
   - User selects database engine from visual grid
   - User pastes connection string
   - Obi confirms connection and activates Scout
   - Redirect to dashboard when complete

4. Auth pages must:
   - Use Supabase Auth
   - Signup creates org, starts 14-day trial, redirects to onboarding
   - Login redirects to dashboard

5. AgentChat.tsx must:
   - Accept agent name as prop (taylor, jordan, shawn)
   - Call /api/agent with message and history
   - Display streaming responses
   - Show agent name and role in chat header
   - Handle handoff signals gracefully

6. Real-time change feed must:
   - Subscribe to Supabase change_events table
   - Show new events as they arrive without page refresh
   - Animate new cards sliding in

7. TrialBanner must:
   - Show days remaining
   - Show upgrade CTA when under 3 days
   - Disappear after conversion

Use Tailwind CSS throughout. Match the dark theme exactly. Build every component completely.
```

---

## Phase 6 — Auth

```
You are implementing authentication for SchemaZero.

Auth requirements:
1. Supabase Auth handles all authentication
2. On signup:
   - Create user in auth.users (Supabase handles this)
   - Create organization record in public.organizations
   - Create user record in public.users with role: owner
   - Set trial_starts_at = now()
   - Set trial_ends_at = now() + 14 days
   - Set plan = trial
   - Redirect to /onboarding

3. Middleware (middleware.ts) must:
   - Protect all /dashboard/* routes
   - Redirect unauthenticated users to /auth/login
   - Check trial status — redirect expired trials to /pricing
   - Allow /auth/* and / to pass through

4. Trial enforcement:
   - Check trial_ends_at on every dashboard load
   - Show TrialBanner with days remaining
   - Block dashboard access when trial expires and plan is still trial
   - Redirect to pricing page with upgrade prompt

Build completely. No placeholders.
```

---

## Phase 7 — Alert Integrations

```
You are building the alert integrations for SchemaZero.

Build the following services in apps/agent/services/:

1. webhook_service.py must:
   - Send HTTP POST to customer-configured webhook URL
   - Always checked and fired first before any other alert channel
   - Payload format (JSON):
     - event: "schema_change"
     - database_name, engine, risk_level
     - change_type, object_type, object_name
     - summary (plain English)
     - next_action (plain English)
     - timestamp
     - dashboard_url
   - Include webhook signing headers for payload verification:
     - SchemaZero-Timestamp: current UNIX timestamp in seconds
     - SchemaZero-Signature: `sha256=` + lowercase hex digest of HMAC-SHA256 over the exact string `{timestamp}.{raw_request_body}`
     - `raw_request_body` means the exact UTF-8 JSON bytes sent on the wire, before parsing or reformatting
     - Use a shared signing secret loaded from environment variable `SCHEMAZERO_WEBHOOK_SIGNING_SECRET` — never hardcode it
     - Receivers must verify the HMAC with the same secret and reject requests whose timestamp is older than 5 minutes to prevent replay attacks
   - Retry once on failure before logging error

2. slack_service.py must:
   - Send formatted Slack messages via webhook URL
   - Message format for HIGH risk:
     - Header: ⚠️ Schema Change Detected — HIGH RISK
     - Database name and engine
     - What changed (object type, name, change type)
     - Impact summary from Zero
     - Next action — what the team should do
     - Link to dashboard
   - Message format for CRITICAL risk:
     - Header: 🚨 CRITICAL Schema Change — Immediate Attention Required
     - Same fields with urgency framing
   - Use Slack Block Kit for formatting

3. pagerduty_service.py must:
   - Create PagerDuty incident via Events API v2
   - Only fires on CRITICAL risk events
   - Incident title: SchemaZero: Critical schema change in [database name]
   - Incident body: full impact analysis summary plus next action
   - Severity: critical
   - Source: schemazero

4. email_service.py must:
   - Send email notifications via SMTP or Resend API
   - HTML email template matching SchemaZero dark theme
   - Include: change summary, risk level, impact analysis, next action, link to dashboard
   - Support per-org email preferences from alert_configs table

5. alert_dispatcher.py in apps/agent/zero/ must:
   - Read org alert_configs from Supabase
   - Check notify_on array against current risk level
   - Route to correct service(s) in this order: webhook first, then Slack, PagerDuty, email
   - Write result to notification_log table
   - Handle service failures gracefully — log error, continue to next channel

Build every file completely. Production-ready Python.
```

---

## Phase 8 — Scout Listeners (All Engines)

```
You are building the database engine listeners for Scout in SchemaZero.

Each listener inherits from base_listener.py and implements the full listen/snapshot cycle for its engine.

Build the following in apps/agent/scout/listeners/:

1. postgres_listener.py:
   - asyncpg connection
   - LISTEN on ddl_command_end using pg_notify
   - Snapshot: query information_schema.columns, tables, indexes, constraints
   - Trigger: CREATE OR REPLACE FUNCTION notify_ddl() in customer DB (read only alternative: poll information_schema every 30s)
   - Fallback to polling if pg_notify not available

2. mysql_listener.py:
   - aiomysql connection
   - Poll information_schema.columns, tables, statistics every 60 seconds
   - Compare against last snapshot stored in Supabase
   - Detect changes and write to change_events

3. mongodb_listener.py:
   - motor (async MongoDB driver) connection
   - Use change streams on admin database
   - Watch for: createCollection, dropCollection, createIndexes, dropIndexes
   - Snapshot: list all collections and their indexes

4. redis_listener.py:
   - aioredis connection
   - Enable keyspace notifications if not enabled
   - Monitor key pattern changes at namespace level (not individual keys)
   - Snapshot: SCAN with pattern matching to map key namespaces and types
   - Poll every 30 seconds for new patterns

Note: SQL Server, Snowflake, and Oracle listeners are coming soon — do not build them yet. Create stub files with a clear NOT_IMPLEMENTED comment so they can be completed later without breaking the runner.

Each listener must:
   - Implement all abstract methods from base_listener.py
   - Update scout_heartbeat every 30 seconds
   - Write detected changes to Supabase change_events
   - Trigger Zero via HTTP call to /internal/analyze endpoint
   - Handle disconnection and reconnect automatically
   - Log errors without crashing the Scout runner

Build every listener completely. Production-ready async Python.
```

---

## Phase 9 — Testing and Deployment Config

```
You are setting up testing and deployment configuration for SchemaZero.

1. Create tests/ directory in apps/agent/ with:
   - test_risk_scorer.py — unit tests for all risk levels
   - test_schema_diff.py — unit tests for postgres diff engine
   - test_alert_dispatcher.py — unit tests for alert routing
   - test_encryption.py — unit tests for connection string encryption
   - Use pytest

2. Create Railway deployment config (railway.toml) in apps/agent/:
   - Build command: pip install -r requirements.txt
   - Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
   - Health check path: /health
   - Restart policy: always

3. Create Vercel deployment config (vercel.json) in apps/web/:
   - Framework: nextjs
   - Build command: next build
   - Output directory: .next
   - Environment variables reference (not values)

4. Create GitHub Actions workflow (even though GitHub integration is community):
   - .github/workflows/deploy.yml
   - On push to main:
     - Run pytest on backend
     - Run next build on frontend
     - Deploy to Railway (backend)
     - Deploy to Vercel (frontend)

5. Create a DEPLOYMENT.md in docs/ with:
   - Step by step deployment guide
   - How to add a new database engine listener
   - How to modify agent behavior via MD files
   - How to add a new alert channel
   - Environment variable reference

Build every file completely.
```

---

## Phase 10 — Final Cleanup

```
You are doing final cleanup and verification for SchemaZero before launch.

1. Verify every agent MD file in /agents/ is complete and follows the pattern from chef.md and taylor.md (from AgentPark/PRKitchen)

2. Verify all FastAPI endpoints return consistent JSON and handle auth correctly

3. Verify the frontend matches the dark theme design with #0a0a0a background and #00e87a accent

4. Verify Scout heartbeat updates correctly and ScoutStatus component shows real status

5. Verify trial logic: signup → 14 days → block → redirect to pricing

6. Implement Lemon Squeezy billing:
   - Solo plan: $19/mo, one Lemon Squeezy variant ID
   - Teams: no Lemon Squeezy price — Contact form only
   - Enterprise: no Lemon Squeezy price — Contact form only
   - Create Lemon Squeezy customer on org creation
   - Lemon Squeezy checkout session for Solo plan upgrade
   - Webhook handler at /api/webhook/lemonsqueezy:
     - order_created → update org plan to solo, set trial_converted = true
     - subscription_cancelled → revert org plan to trial, set trial_ends_at = now()
   - Store lemonsqueezy_customer_id and lemonsqueezy_subscription_id on organizations table
   - Verify webhook handles both order completion and subscription cancellation

7. Settings page billing section must:
   - Show current plan
   - Show trial days remaining if on trial
   - Show Upgrade to Solo button for trial users
   - Show Manage Subscription button for Solo users
   - Show Cancel Subscription option
   - Show contact form for Teams and Enterprise interest — CREATE_LEAD signal to Jordan

9. Remove build.md from the repository

10. Update README.md build phase checklist — mark all phases complete

11. Create a CHANGELOG.md in docs/ with initial v0.1.0 entry listing everything built

12. Final check: make sure no real agent names (Scout, Zero, Obi, Sully, Sal) appear in any public-facing file or the README. Public files use placeholder names only.

Verify everything is complete and production ready.
```

---

## Notes for Claude Code

- Always read the relevant agent MD file before building code that calls it
- Never hardcode connection strings, API keys, or secrets
- Always use environment variables via python-dotenv (backend) and Next.js env (frontend)
- The customer's database is always read-only — SchemaZero never writes to it
- Agent MD files are the source of truth for agent behavior — code just loads and calls them
- When in doubt about agent behavior, check the MD file first

---

*Remove this file from the repository when the build is complete.*
