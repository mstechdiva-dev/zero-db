# SchemaZero User Guide

SchemaZero watches your database schema for changes, analyzes the impact using AI, scores the risk, and alerts your team — before a change becomes a production incident.

---

## Table of Contents

1. [Connecting Your Database](#connecting-your-database)
2. [PostgreSQL & Compatible](#postgresql--compatible)
   - [Local Postgres](#local-postgres)
   - [Neon](#neon)
   - [Supabase (Direct Connection)](#supabase-direct-connection)
   - [Supabase (Connection Pooler)](#supabase-connection-pooler)
   - [CockroachDB](#cockroachdb)
   - [AWS RDS](#aws-rds)
   - [Heroku Postgres](#heroku-postgres)
   - [Railway Postgres](#railway-postgres)
   - [ElephantSQL](#elephantsql)
   - [Timescale Cloud](#timescale-cloud)
3. [MySQL / MariaDB](#mysql--mariadb)
4. [MongoDB](#mongodb)
5. [Redis](#redis)
6. [Coming Soon](#coming-soon)
7. [SSL Reference](#ssl-reference)
8. [How Scout Watches Each Engine](#how-scout-watches-each-engine)
9. [Alert Channels](#alert-channels)
10. [Risk Levels](#risk-levels)
11. [Troubleshooting](#troubleshooting)

---

## Connecting Your Database

SchemaZero connects to your database in **read-only mode**. It never writes to your customer database — it only reads schema structure (table definitions, columns, indexes, constraints). Your data is never touched.

You provide a connection string during onboarding. SchemaZero encrypts it with AES-256 before storing it.

**Supported engines:**

| Engine | Change Detection | Status |
|--------|-----------------|--------|
| PostgreSQL (all variants) | `pg_notify` DDL trigger + polling fallback | Available |
| Supabase | `pg_notify` (direct) or polling (pooler) | Available |
| Neon | `pg_notify` + auto-reconnect on pause | Available |
| CockroachDB | `pg_notify` + polling fallback | Available |
| MySQL / MariaDB | Polling `information_schema` | Available |
| MongoDB | Change streams | Available |
| Redis | Keyspace notifications + namespace polling | Available |
| SQL Server | — | Coming soon |
| Snowflake | — | Coming soon |
| Oracle | — | Coming soon |

---

## PostgreSQL & Compatible

SchemaZero handles SSL mode, scheme normalization (`postgres://` vs `postgresql://`), and reconnection automatically for all Postgres-compatible databases. You can paste your connection string as-is from your provider's dashboard.

### Local Postgres

No SSL required. Standard connection string format.

```
postgresql://user:password@localhost:5432/mydb
```

Or using the `postgres://` scheme (both work):

```
postgres://user:password@localhost/mydb
```

**Scout behavior:** Attempts to install a DDL event trigger for real-time `pg_notify`. Falls back to polling `information_schema` every 30 seconds if the trigger cannot be installed (e.g., insufficient privileges).

---

### Neon

Neon is a serverless Postgres provider that auto-pauses compute when idle. SchemaZero handles this transparently — when Neon wakes the compute after a pause, SchemaZero reconnects automatically.

**Connection string from Neon dashboard:**

```
postgresql://user:password@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
```

You can also omit `?sslmode=require` — SchemaZero detects `*.neon.tech` and applies SSL automatically:

```
postgresql://user:password@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb
```

**Scout behavior:** Uses `pg_notify` via DDL event trigger. If Neon pauses the compute and drops the connection, Scout reconnects with backoff (5s → 10s → 20s → 30s → 60s). No schema changes are missed — Scout takes a fresh snapshot on reconnect and diffs against the last known state.

---

### Supabase (Direct Connection)

Use the direct connection string from **Project Settings → Database → Connection string → URI**. This is the standard Postgres connection on port 5432.

```
postgresql://postgres:your-password@db.abcdefghijkl.supabase.co:5432/postgres
```

SchemaZero detects `*.supabase.co` and applies SSL automatically. Adding `?sslmode=require` explicitly also works.

**Scout behavior:** Uses `pg_notify` via DDL event trigger. Falls back to polling if insufficient privileges.

---

### Supabase (Connection Pooler)

Supabase also offers a **PgBouncer connection pooler** on port **6543**. This is the URL labeled "Connection pooling" in your Supabase dashboard.

```
postgresql://postgres:your-password@db.abcdefghijkl.supabase.co:6543/postgres
```

> **Important:** PgBouncer in transaction mode does not support `LISTEN`/`NOTIFY` commands. SchemaZero automatically detects port 6543 and switches to polling mode. There is no change in setup required — SchemaZero handles this automatically.

**Scout behavior:** Polling only (every 30 seconds). `statement_cache_size` is set to 0 as required by PgBouncer transaction mode. `pg_notify` is not attempted.

**Recommendation:** For real-time change detection, prefer the **direct connection** (port 5432) when possible. Use the pooler connection if you are on a Supabase plan with a low direct connection limit.

---

### CockroachDB

CockroachDB is Postgres-compatible and works with all SchemaZero features. It uses port 26257 by default and requires full SSL certificate verification.

**Connection string from CockroachDB Cloud:**

```
postgresql://user:password@free-tier.gcp-us-central1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full
```

You can omit `?sslmode=verify-full` — SchemaZero detects `*.cockroachlabs.cloud` and `*.cockroachdb.com` and applies `verify-full` automatically:

```
postgresql://user:password@free-tier.gcp-us-central1.cockroachlabs.cloud:26257/defaultdb
```

**Scout behavior:** Attempts `pg_notify` via DDL event trigger. Falls back to polling if the trigger cannot be installed.

---

### AWS RDS

Use the endpoint from your RDS instance dashboard. SSL is applied automatically for `*.rds.amazonaws.com` hosts.

```
postgresql://user:password@mydb.abc123xyz.us-east-1.rds.amazonaws.com:5432/mydb
```

To enforce SSL explicitly:

```
postgresql://user:password@mydb.abc123xyz.us-east-1.rds.amazonaws.com:5432/mydb?sslmode=require
```

**Scout behavior:** Attempts `pg_notify`. Falls back to polling if RDS permissions do not allow event trigger creation (common on RDS — the `rds_superuser` role is required for event triggers).

---

### Heroku Postgres

Heroku provides a `DATABASE_URL` environment variable. SSL is applied automatically for Heroku hosts.

```
postgres://user:password@ec2-12-34-56-78.compute-1.amazonaws.com:5432/mydb
```

Note: Heroku connection strings use `postgres://` (not `postgresql://`). SchemaZero normalizes this automatically.

**Scout behavior:** Attempts `pg_notify`. Falls back to polling.

---

### Railway Postgres

Railway generates a connection string under **Variables → DATABASE_URL** in your service.

```
postgresql://postgres:password@containers-us-west-123.railway.app:6789/railway
```

Railway internal connections (within the same Railway project) use the private network:

```
postgresql://postgres:password@postgres.railway.internal:5432/railway
```

**Scout behavior:** Attempts `pg_notify`. Falls back to polling.

---

### ElephantSQL

ElephantSQL connection strings are found in your instance dashboard under **Details**.

```
postgresql://user:password@chunee.db.elephantsql.com/dbname
```

SSL is applied automatically for `*.elephantsql.com` hosts.

**Scout behavior:** Attempts `pg_notify`. Falls back to polling.

---

### Timescale Cloud

Timescale Cloud is a Postgres-compatible time-series database. SSL is applied automatically for `*.timescaledb.io` hosts.

```
postgresql://tsdbadmin:password@abc123.a.timescaledb.io:30000/tsdb
```

**Scout behavior:** Attempts `pg_notify`. Falls back to polling.

---

## MySQL / MariaDB

SchemaZero polls `information_schema` every 60 seconds to detect schema changes. MySQL/MariaDB does not support `LISTEN`/`NOTIFY`, so polling is the only available method.

**Connection string format:**

```
mysql://user:password@host:3306/dbname
```

**Examples:**

```
# Local MySQL
mysql://root:password@localhost:3306/myapp

# PlanetScale (MySQL-compatible serverless)
mysql://user:password@aws.connect.psdb.cloud/dbname?ssl-mode=REQUIRED

# Amazon Aurora MySQL
mysql://admin:password@mydb.abc123.us-east-1.rds.amazonaws.com:3306/mydb

# Railway MySQL
mysql://root:password@containers-us-west-123.railway.app:6789/railway
```

**What Scout detects:**
- Tables added or dropped
- Columns added, dropped, or modified (type, nullability, default)
- Indexes added or dropped

---

## MongoDB

SchemaZero uses **change streams** on your MongoDB database to watch for collection and index changes in real time. Change streams require MongoDB 3.6+ and a replica set or sharded cluster (change streams are not available on standalone instances).

**Connection string format:**

```
mongodb://user:password@host:27017/dbname
mongodb+srv://user:password@cluster.mongodb.net/dbname
```

**Examples:**

```
# MongoDB Atlas (cloud)
mongodb+srv://user:password@cluster0.abc123.mongodb.net/mydb

# Local MongoDB replica set
mongodb://localhost:27017/mydb?replicaSet=rs0

# MongoDB Atlas serverless
mongodb+srv://user:password@instance.abc123.mongodb.net/mydb
```

> **Note:** MongoDB Atlas free tier (M0) does not support change streams. Upgrade to M10 or higher to use SchemaZero with Atlas.

**What Scout detects:**
- Collections added or dropped
- Indexes added or dropped
- Validation schema changes

---

## Redis

SchemaZero monitors Redis **key namespaces** (not individual keys). It groups keys by their prefix (the part before the first `:`) and detects when new namespace patterns appear, existing ones disappear, key types change, or TTL policies change.

SchemaZero enables keyspace notifications automatically when connecting. This requires `CONFIG SET notify-keyspace-events KEA` permission. If your Redis instance does not allow `CONFIG SET` (common on managed Redis), SchemaZero falls back to polling every 30 seconds.

**Connection string format:**

```
redis://user:password@host:6379/0
rediss://user:password@host:6379/0   ← TLS
```

**Examples:**

```
# Local Redis
redis://localhost:6379/0

# Upstash (serverless Redis, TLS required)
rediss://default:password@global-champion-abc123.upstash.io:6379

# Redis Cloud
redis://default:password@redis-abc123.c1.us-east-1-mz.ec2.cloud.redislabs.com:12345

# Railway Redis
redis://default:password@containers-us-west-123.railway.app:6379

# AWS ElastiCache (TLS)
rediss://user:password@clustercfg.myredis.abc123.use1.cache.amazonaws.com:6379
```

**What Scout detects:**
- New key namespace patterns (e.g., `session:*` appears)
- Dropped key namespace patterns
- Key type changes at namespace level (e.g., `cache:*` changes from `string` to `hash`)
- TTL policy changes (namespace starts or stops using TTL)

---

## Coming Soon

The following engines are on the roadmap. Stub listeners exist in the codebase and will be completed in a future release.

| Engine | Detection Method (planned) |
|--------|---------------------------|
| SQL Server | Polling `sys.objects`, `sys.columns` |
| Snowflake | Polling `INFORMATION_SCHEMA.TABLES` |
| Oracle | Polling `ALL_OBJECTS`, `ALL_TAB_COLUMNS` |

---

## SSL Reference

SchemaZero applies SSL settings automatically based on the host, but you can override them explicitly by including `?sslmode=…` in your connection string (Postgres only).

| `sslmode` value | Behavior |
|-----------------|----------|
| `disable` | No SSL. Use only for local development. |
| `require` | Encrypted connection. Certificate is not verified. Most cloud providers. |
| `verify-ca` | Encrypted. CA certificate verified, but hostname is not checked. |
| `verify-full` | Encrypted. Full hostname + certificate chain verified. CockroachDB default. |
| *(absent)* | Provider default applied automatically, or asyncpg decides. |

**Automatic SSL defaults by provider:**

| Provider / Host Suffix | Applied `sslmode` |
|-----------------------|-------------------|
| `localhost`, `127.0.0.1` | none (no SSL) |
| `*.neon.tech` | `require` |
| `*.supabase.co`, `*.supabase.in` | `require` |
| `*.rds.amazonaws.com` | `require` |
| `*.heroku.com` | `require` |
| `*.elephantsql.com` | `require` |
| `*.timescaledb.io` | `require` |
| `*.cockroachlabs.cloud`, `*.cockroachdb.com` | `verify-full` |
| All others | asyncpg default (attempts TLS, falls back) |

---

## How Scout Watches Each Engine

| Engine | Primary Method | Fallback |
|--------|---------------|---------|
| Postgres (direct) | `pg_notify` via DDL event trigger (real-time) | Poll `information_schema` every 30s |
| Postgres (pooler/PgBouncer) | — | Poll `information_schema` every 30s |
| MySQL / MariaDB | — | Poll `information_schema` every 60s |
| MongoDB | Change streams (real-time) | — |
| Redis | Keyspace notifications | Poll key namespaces every 30s |

Scout sends a **heartbeat** to SchemaZero every 30 seconds. The dashboard shows a green status indicator when the heartbeat is current. If Scout misses 3 heartbeats (90 seconds), the indicator turns red.

---

## Alert Channels

Configure alert channels in **Dashboard → Settings → Alerts**.

### Custom Webhook

SchemaZero fires your webhook first, before any other channel. Every request is signed so you can verify it came from SchemaZero.

**Payload:**
```json
{
  "event": "schema_change",
  "database_name": "production-db",
  "engine": "postgres",
  "risk_level": "HIGH",
  "change_type": "column_dropped",
  "object_type": "column",
  "object_name": "users.email",
  "summary": "The email column was dropped from the users table...",
  "next_action": "Do not deploy until this is resolved. Verify all queries referencing users.email.",
  "timestamp": 1712345678,
  "dashboard_url": "https://app.schemazero.com/dashboard"
}
```

**Verifying the signature:**
```
SchemaZero-Timestamp: <unix seconds>
SchemaZero-Signature: sha256=<hex>
```

The signature is `HMAC-SHA256` over `{timestamp}.{raw_request_body}` using your webhook signing secret. Reject requests where the timestamp is more than 5 minutes old.

### Slack

Sends Block Kit formatted messages to your Slack channel. Fires on HIGH and CRITICAL risk events. Configure the Slack Incoming Webhook URL in Settings.

### PagerDuty

Creates a PagerDuty incident via Events API v2. Fires on CRITICAL risk events only. Requires a PagerDuty Integration Key (Routing Key).

### Email

Sends HTML email notifications to configured recipients. Fires based on your `notify_on` settings (default: HIGH and CRITICAL). Requires SMTP credentials or Resend API configuration.

**Alert firing order:** Webhook → Slack → PagerDuty → Email. A failure in one channel does not prevent the others from firing.

---

## Risk Levels

Every schema change is scored automatically by Zero (the AI impact analyzer).

| Level | Color | Meaning | Default next action |
|-------|-------|---------|-------------------|
| **LOW** | Green | Additive change. No breaking risk. | Safe to deploy. No action required. |
| **MEDIUM** | Yellow | Non-breaking but warrants review. | Review [specific thing] before deploying. |
| **HIGH** | Orange | Potentially breaking. Do not deploy without verification. | Do not deploy until this is resolved. |
| **CRITICAL** | Red | Destructive or breaking. Requires immediate escalation. | Stop. Escalate immediately. |

**Scoring rules:**

| Change | Risk Level |
|--------|-----------|
| Column added (nullable) | LOW |
| Index added | LOW |
| Column type widened (e.g., `int` → `bigint`) | MEDIUM |
| Constraint added | MEDIUM |
| Index dropped (low-traffic table) | MEDIUM |
| Column dropped | HIGH |
| NOT NULL added to existing column | HIGH |
| Index dropped (critical table) | HIGH |
| Table dropped | CRITICAL |
| Primary key changed | CRITICAL |
| Foreign key constraint dropped | CRITICAL |

---

## Troubleshooting

### Scout shows as offline / no heartbeat

- Verify your connection string is correct and the database is reachable from Railway (the SchemaZero backend).
- Check that the database user has at least `SELECT` privileges on `information_schema`.
- For Neon: the compute may be paused. SchemaZero will reconnect automatically when it wakes. If it stays offline, check the Railway logs.

### pg_notify not working / falling back to polling

This is expected in several situations:
- **Supabase pooler (port 6543):** PgBouncer does not support `LISTEN`. Use the direct connection (port 5432) for real-time detection.
- **Insufficient privileges:** Event trigger creation requires superuser or `rds_superuser` on RDS. If you cannot grant this, polling every 30 seconds is the fallback.
- **Managed Postgres with restricted DDL:** Some providers block `CREATE EVENT TRIGGER`. Polling still works correctly.

### Connection refused or SSL errors

- Ensure the connection string uses `postgresql://` or `postgres://` (both are accepted).
- For local Postgres, make sure `pg_hba.conf` allows connections from SchemaZero's Railway IP range.
- If you see `SSL SYSCALL error`, try adding `?sslmode=require` explicitly to your connection string.
- For CockroachDB, `sslmode=verify-full` is required and applied automatically — ensure your server certificate is valid.

### MySQL: no changes detected

- Verify the database user has `SELECT` on `information_schema`.
- SchemaZero polls every 60 seconds — changes may take up to a minute to appear.
- Ensure the schema name is specified in the connection string path (e.g., `mysql://user:pass@host/myschema`).

### MongoDB: "change streams not supported"

Change streams require a replica set or sharded cluster. MongoDB Atlas M0 (free tier) does not support change streams. Upgrade to M10+ or run a local replica set.

### Redis: keyspace notifications not received

- If your Redis instance does not allow `CONFIG SET`, SchemaZero falls back to polling every 30 seconds automatically.
- Upstash Redis requires TLS — use `rediss://` (double-s) in your connection string.
- AWS ElastiCache: keyspace notifications require `notify-keyspace-events` to be set in your parameter group. SchemaZero will attempt to set it but may be blocked by IAM policy.
