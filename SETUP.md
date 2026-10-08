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
2. Open **SQL Editor** and run these files from this repo, **in this order**, one at a time:

   | # | File | What it does |
   |---|---|---|
   | 0 | `supabase/schema.sql` | Base tables, security rules, sign-up trigger |
   | 1 | `supabase/migrations/001_cleanup.sql` | Lemon Squeezy columns, `webhook` alert channel, webhook URL, `next_action` |
   | 2 | `supabase/migrations/002_leads.sql` | Sales leads table (admin panel) |
   | 3 | `supabase/migrations/003_agent_versions.sql` | Saved agent edits (admin panel) |
   | 4 | `supabase/migrations/004_lemonsqueezy.sql` | Billing portal column |
   | 5 | `supabase/migrations/005_waitlist.sql` | **Waitlist table. The "Join waitlist" form fails without it.** |
   | 6 | `supabase/migrations/006_change_types.sql` | Change types Scout writes. **Without it, new tables and new indexes are never recorded.** |

   Already set up before? Run only the ones you haven't. `002`, `004`, `005` and `006` are safe to run again. `000`, `001` and `003` are not: they fail with an "already exists" error if repeated. `docs/db_migrations.md` is the log of what has run.
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
   | `DASHBOARD_URL` | Required | Where alert links point, e.g. `https://yourdomain.com`. Default is `https://app.schemazero.com`. |
   | `INTERNAL_API_SECRET` | Recommended | From step 2. Protects the Scout-to-Zero call. If unset, only calls from the same machine are accepted, which is safe for this single-service setup. |
   | `SCHEMAZERO_WEBHOOK_SIGNING_SECRET` | If using custom webhooks | From step 2. Without it, webhooks are sent unsigned. |
   | `SLACK_WEBHOOK_URL` | Optional | Default Slack hook for orgs that haven't set their own |
   | `PAGERDUTY_API_KEY` | Optional | Default PagerDuty Events v2 key, same idea |
   | `SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASSWORD` | For email alerts | Any SMTP server. Port defaults to 587. With no `SMTP_HOST`, email alerts are skipped. |
   | `EMAIL_FROM` | Optional | Sender address. Default `alerts@schemazero.com` |
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
   | `NEXT_PUBLIC_LEMONSQUEEZY_STORE_ID` | For billing | Lemon Squeezy store ID |
   | `LEMONSQUEEZY_API_KEY` | For billing | Lemon Squeezy API key |
   | `LEMONSQUEEZY_SOLO_VARIANT_ID` | For billing | Variant ID of the Solo plan |
   | `LEMONSQUEEZY_WEBHOOK_SECRET` | For billing | Signing secret for the webhook below |

4. Billing only: in Lemon Squeezy add a webhook pointing to `https://<your-site>/api/webhook/lemonsqueezy` using the same secret.
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
| `Failed to write change_event` | A database migration is missing. Run `006` (and check `001`). |
| `Failed to decrypt connection string` | `ENCRYPTION_KEY` differs from the one used when the database was connected |
| `Zero agent prompt not loaded` | The image was built without the `agents/` folder. Redeploy from the repo root. |
| `pg_notify setup failed ... falling back to polling` | The database user can't create event triggers. Changes arrive every 30 seconds. |
| `Webhook send error` / `Slack send error` | The destination URL rejected the call. Check the URL in Settings. |
| Secure box says "private network" | The host resolves to a private address. Use the database's public address. (`ALLOW_PRIVATE_DB_HOSTS=1` lifts this for local development only. Never set it in production.) |
| `Heartbeat update failed` | Migration `000` didn't run fully. Re-check `supabase/schema.sql`. |

Dashboard shows Scout offline: the backend hasn't written a heartbeat in 90 seconds. Check `/health` and the Railway logs.

---

## 6. GitHub workflow (optional)

`.github/workflows/deploy.yml` is **manual only** (Actions tab → Run workflow). It isn't needed: Vercel and Railway deploy from GitHub on their own. If you do run it, it needs these repo **secrets**:

`ENCRYPTION_KEY`, `ANTHROPIC_API_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `NEXT_PUBLIC_LEMONSQUEEZY_STORE_ID`, `RAILWAY_API_URL`, `RAILWAY_TOKEN`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`

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

## Known limits

- **Connection strings never go through the chat.** The secure box sends them straight to the backend. The chat refuses messages containing a password.
- **Impact analysis reads your schema, not your code.** Claude is told what changed and writes up what is likely affected. It does not know your file names or line numbers.
- **The "blocked before merge" pull request check shown in the demo is not built yet.**
- Engines not yet supported: SQL Server, Snowflake, Oracle (listed as "soon" on the site).
