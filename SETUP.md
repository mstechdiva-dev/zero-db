# SchemaZero Setup

Every setting needed to run SchemaZero, in the order to do them.

| Piece | Where it runs | What it does |
|---|---|---|
| Database + login | Supabase | Stores orgs, change events, alerts; handles sign-in |
| Website + dashboard | Vercel (`apps/web`) | Landing page, demo, waitlist, dashboard, admin |
| Backend (Scout + Zero) | Railway (`apps/agent`) | Watches your databases, scores changes, sends alerts |
| AI | Anthropic API | Writes the plain-English impact summaries |

The backend has to run on something that stays on all day (Railway). Vercel can't host it because Scout keeps open connections to your databases.

**Minimum for the demo site and waitlist:** step 1 (database) and the three Supabase variables in step 4 (website). Everything else turns on a feature, and the tables say which.

---

## 1. Supabase

1. Create a project at supabase.com.
2. Open **SQL Editor** and run **one file**: `supabase/schema.sql`. It is the complete, final schema and already includes everything the older migration files added. A new project needs nothing else.

   **Already have tables in this project?** For example from an older version, or you saw `type "change_type" does not exist`. Run `supabase/reset.sql` first, then `supabase/schema.sql`:
   - `reset.sql` **deletes** SchemaZero's tables and data: organizations, users, connected databases and their saved connection strings, change events, alerts and logs.
   - It **keeps** your login accounts, the waitlist, sales leads, and prompts saved in the admin panel.
   - `schema.sql` then rebuilds everything and gives each existing login a fresh organization, so people can sign in again.
   - If `schema.sql` says "SchemaZero tables already exist", the reset didn't run. Run it first.

   Check it worked by running this. You should see 11 tables, including `change_events`, `connected_databases`, `waitlist`, and `organizations`:
   ```sql
   select table_name from information_schema.tables
   where table_schema = 'public' order by table_name;
   ```

   **Already ran an earlier copy of `schema.sql`?** Also run `supabase/migrations/008_mongo_change_types.sql`. It adds two change types the MongoDB listener writes (`collection_created`, `schema_change`) that the first version of the file left out. It's two lines and safe to run again. A database created from the current `schema.sql` already has them. Also run `supabase/migrations/009_trial_reminders.sql` (one column, safe to run again) so trial reminder emails can remember what they sent. And `supabase/migrations/010_plans_table.sql` (the plans table; the backend won't start watching without it).

   The other files in `supabase/migrations/` are history for databases built from earlier versions of `schema.sql`. You don't need them. `docs/db_migrations.md` explains.
3. **Project Settings → API**. Copy three values you'll need below:
   - Project URL → `NEXT_PUBLIC_SUPABASE_URL`
   - `anon` `public` key → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY` (**secret**: server only, never in browser code)
4. **Authentication → URL Configuration**: set the Site URL to your website address (and add it to the redirect URLs) so sign-up emails link back to the right place.

---

## 2. Generate two secrets

```bash
# ENCRYPTION_KEY: encrypts stored database connection strings (AES-256)
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# INTERNAL_API_SECRET and SCHEMAZERO_WEBHOOK_SIGNING_SECRET: any long random string
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Keep `ENCRYPTION_KEY` somewhere safe. If it changes, every stored connection string becomes unreadable.

---

## 3. Railway (backend)

1. New project → **Deploy from GitHub repo** → pick this repo.
2. Leave the **root directory as the repo root**. The root `railway.toml` tells Railway to build `Dockerfile.agent`, which packages `apps/agent` together with the `agents/` prompt files the backend needs.
3. Add these **variables**:

   | Variable | Needed? | What it is |
   |---|---|---|
   | `NEXT_PUBLIC_SUPABASE_URL` | Required | Supabase project URL |
   | `SUPABASE_SERVICE_ROLE_KEY` | Required | Supabase service role key |
   | `ANTHROPIC_API_KEY` | Required | Key from console.anthropic.com. Without it the AI analysis fails. |
   | `ENCRYPTION_KEY` | Required | From step 2 |
   | `FRONTEND_URL` | Required | Your website address, e.g. `https://yourdomain.com`. The backend only accepts browser calls from here. Default is `https://schemazero.com`. |
   | `DASHBOARD_URL` | Required | Where alert links point. Same as your website address, e.g. `https://schemazero.com`. Default is `https://schemazero.com`. |
   | `INTERNAL_API_SECRET` | Recommended | From step 2. Protects the Scout-to-Zero call. If unset, only calls from the same machine are accepted, which is safe for this single-service setup. |
   | `SCHEMAZERO_WEBHOOK_SIGNING_SECRET` | If using custom webhooks | From step 2. Without it, webhooks are sent unsigned. |
   | `SLACK_WEBHOOK_URL` | Optional | Default Slack hook for orgs that haven't set their own |
   | `PAGERDUTY_API_KEY` | Optional | Default PagerDuty Events v2 key, same idea |
   | `SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASSWORD` | For email alerts | Any SMTP server. Port defaults to 587. With no `SMTP_HOST`, email alerts are skipped. |
   | `EMAIL_FROM` | Optional | Sender address. Default `schemazero@xyzagents.ai` |
   | `ALLOW_PRIVATE_DB_HOSTS` | Never in production | `1` allows connecting to private addresses. Local development and tests only. |
| `INTERNAL_API_URL` | Leave unset | Defaults to the backend's own port. Only set it if you split Scout and Zero into separate services. |
   | `PORT` | Automatic | Railway sets this |

4. **Settings → Networking → Generate domain** to get the public address.
5. Check it's alive: open `https://<your-railway-domain>/health`. You should see `{"status":"ok", ...}`.

Redeploys happen on every push to `main` through Railway's own GitHub connection. You don't need the GitHub workflow for this.

---

## 4. Vercel (website)

1. Import the repo. Set **Root Directory** to `apps/web`.
2. Turn on **Include source files outside of the Root Directory** (Settings → General). The admin Agents pages read the `agents/` folder from disk.
3. Add these **environment variables**:

   | Variable | Needed? | What it is |
   |---|---|---|
   | `NEXT_PUBLIC_SUPABASE_URL` | Required | Supabase project URL |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Required | Supabase anon key |
   | `SUPABASE_SERVICE_ROLE_KEY` | Required | Used by the waitlist, admin panel and billing webhook. Server only. |
   | `RAILWAY_API_URL` | For the chats | Your Railway address from step 3, no trailing slash. The pricing and onboarding chats show an error without it. |
   | `ADMIN_EMAIL` | For `/admin` | Comma-separated emails allowed into the admin panel |
   | `STRIPE_SECRET_KEY` | For billing | Stripe secret key (`sk_test_…` while testing, `sk_live_…` for real money). Server only. |
   | `STRIPE_PRICE_ID_SOLO` | For billing | ID of the Solo plan's price (`price_…`) |
   | `STRIPE_WEBHOOK_SECRET` | For billing | Signing secret of the webhook in the next step (`whsec_…`) |

4. Billing only, in the Stripe dashboard (start in **test mode**):
   1. **Product catalog**: create a product "Solo" with a recurring price of $19 per month. Copy the price ID into `STRIPE_PRICE_ID_SOLO`.
   2. **Developers → Webhooks → Add endpoint**: URL `https://<your-site>/api/webhook/stripe`, and send these events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`. Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.
   3. **Settings → Billing → Customer portal**: turn it on (this is what the "Manage subscription" button opens).
   4. Try it: Settings → Upgrade → pay with the test card `4242 4242 4242 4242`. The plan should switch to Solo within a few seconds. Then repeat with your live keys and a live price when you're ready for real money.
   - The free trial needs no card and is tracked in SchemaZero, not Stripe. Teams stays on the waitlist.
5. Deploy. Vercel redeploys on every push, and each pull request gets its own preview.

---

## 5. Check it works (test drop)

1. Open the site and sign up. On **Onboarding**, chat with Obi if you want help, and paste your connection string into the **secure box** (not the chat). The backend tests the connection, then saves it encrypted. Scout starts watching within about a minute.
   - The database must be reachable from the internet. A database on `localhost` or a private network is refused. If it has an IP allow list, allow your Railway service.
   - **Postgres, Supabase (port 5432), Neon, CockroachDB:** the database user needs permission to create event triggers (the `postgres` role on Supabase has it). With it, changes show up in under a second. Without it, Scout falls back to checking every 30 seconds.
   - **Supabase pooler (port 6543):** polling only, every 30 seconds.
   - **MySQL / MariaDB:** polling every 60 seconds. **MongoDB Atlas** needs M10 or higher. **Redis:** 30-second polling.
2. In **Dashboard → Settings**, add an alert channel (webhook, Slack, PagerDuty or email) and use **test send**.
3. Run a change against the test database, for example:
   ```sql
   ALTER TABLE users DROP COLUMN legacy_email;
   ```
4. Expect: a HIGH change in the dashboard feed, an impact summary, and an alert on each channel you set up.

If nothing shows up, look at the Railway logs:

| You see | Meaning |
|---|---|
| `Failed to write change_event` | The database doesn't match the code. Re-run the schema steps in section 1 (`reset.sql`, then `schema.sql`). |
| `Failed to decrypt connection string` | `ENCRYPTION_KEY` differs from the one used when the database was connected |
| `Zero agent prompt not loaded` | The image was built without the `agents/` folder. Redeploy from the repo root. |
| `pg_notify setup failed ... falling back to polling` | The database user can't create event triggers. Changes arrive every 30 seconds. |
| `Webhook send error` / `Slack send error` | The destination URL rejected the call. Check the URL in Settings. |
| Secure box says "private network" | The host resolves to a private address. Use the database's public address. (`ALLOW_PRIVATE_DB_HOSTS=1` lifts this for local development only. Never set it in production.) |
| `Heartbeat update failed` | The database doesn't match the code. Re-run the schema steps in section 1. |

Dashboard shows Scout offline: the backend hasn't written a heartbeat in 90 seconds. Check `/health` and the Railway logs.

---

## 6. GitHub workflow (optional)

`.github/workflows/deploy.yml` is **manual only** (Actions tab → Run workflow). It isn't needed: Vercel and Railway deploy from GitHub on their own. If you do run it, it needs these repo **secrets**:

`ENCRYPTION_KEY`, `ANTHROPIC_API_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `RAILWAY_API_URL`, `RAILWAY_TOKEN`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`

---

## 7. Local development and tests

```bash
# Website (http://localhost:3000): put its variables in apps/web/.env.local
cd apps/web && npm install && npm run dev

# Backend (http://localhost:8000): put its variables in apps/agent/.env
cd apps/agent
pip install -r requirements.txt pytest pytest-asyncio
uvicorn main:app --reload
pytest tests/                   # unit tests
```

`.env.example` lists every variable.

The end-to-end test creates a table called `zero_e2e_users` on a real Postgres, drops a column from it, and follows the change through Scout, Zero and a signed webhook. It only runs when you point it at a **throwaway** Postgres (it needs permission to create event triggers):

```bash
ZERO_TEST_PG_DSN=postgresql://postgres@127.0.0.1:5432/scratch pytest tests/test_pipeline_e2e.py
```

---

## Pre-merge schema check (optional)

`apps/agent/premerge_check.py` reads SQL migration files and flags risky changes (dropped columns or tables, renames, NOT NULL, dropped keys) using the same risk levels as Zero. It reads the SQL text only: no database connection and no Claude call.

```
cd apps/agent
python premerge_check.py ../../supabase/migrations/009_cleanup.sql
python premerge_check.py --fail-on critical file.sql
```

It exits with 1 when anything is at or above `--fail-on` (default `high`). The workflow `.github/workflows/premerge-check.yml` runs it on the SQL files changed since a branch you pick. It is manual-only like the other workflow; the file explains how to run it on every pull request and make it a required check so it blocks merging.

It cannot see the old column type, so a type change shows as medium ("review"). It also does not look for the code that still uses a dropped column; that part is not built.

## Known limits

- **Private-network blocking has one gap.** The connection form refuses private and local addresses, including the servers a `mongodb+srv` name points to. But the check looks the name up once and the database driver looks it up again when it connects, so a DNS server that answers differently the second time could slip past. Rare, and it needs a signed-in user, but it's why new sign-ups are best kept to people you invited.
- **Connection strings never go through the chat.** The secure box sends them straight to the backend. The chat refuses messages containing a password.
- **Impact analysis reads your schema, not your code.** Claude is told what changed and writes up what is likely affected. It does not know your file names or line numbers.
- **The "blocked before merge" pull request check shown in the demo is not built yet.**
- Engines not yet supported: SQL Server, Snowflake, Oracle (listed as "soon" on the site).
