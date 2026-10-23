# Provider test sheet

Before the site names a provider as working, someone runs this check against a real database on that provider and records the result here. Nothing goes on the site on "should work".

## How to run it

Use a throwaway database. The check creates and drops only tables named `sz_check_*` and removes the trigger Scout installs.

```bash
cd apps/agent
python provider_check.py "postgresql://USER:PASS@HOST:5432/DB"
```

Pooled connections (Supabase port 6543, Neon hosts with `-pooler`) cannot use the instant trigger, so Scout polls every 30 seconds. Make the changes over the direct string and let Scout watch the pooled one:

```bash
python provider_check.py "POOLED_STRING" --ddl-dsn "DIRECT_STRING" --wait 75
```

The output shows the provider Scout detected, whether it is using the instant trigger or polling, and PASS or FAIL with the time for each of four changes (add column, drop column, create index, drop table). Exit code 0 means all four were caught.

Record, for each run: provider, direct or pooled, instant or polling, result, date, who ran it.

## Postgres-compatible providers (use `provider_check.py`)

Run each one twice where the provider offers both direct and pooled strings.

| Provider | Direct | Pooled | Notes to record |
|---|---|---|---|
| Supabase | not run | not run | Port 5432 direct, 6543 pooled. Does the account allow the trigger? |
| Neon | not run | not run | Pooled host has `-pooler`. Check a paused database wakes and reconnects. |
| AWS RDS / Aurora Postgres | not run | n/a | Needs `rds_superuser` for the trigger. If not, expect polling. |
| Google Cloud SQL / AlloyDB | not run | n/a | Trigger permission varies by role. |
| Azure Database for PostgreSQL | not run | n/a | Check SSL requirement. |
| Heroku Postgres | not run | n/a | Hosts ending `.heroku.com` get SSL by default. |
| DigitalOcean, Aiven, Crunchy Bridge, Railway, Render, Timescale | not run | n/a | Run only the ones you have an account for. |

Pass means all four changes caught. Polling that catches all four is still a pass, but the site must say "about 30 seconds" for that provider, not "within seconds".

## Tested locally already (not on a hosted service)

Postgres 16 direct (caught in under a second), Postgres 16 behind PgBouncer on port 6543 (polling, about 30s), CockroachDB 24.3 (polling, about 30s). These were local servers, so they do not count for the hosted providers above.

## Not Postgres: no script yet

| Service | What to check by hand | Expected |
|---|---|---|
| Amazon Redshift | Try connecting with a `postgresql://` string in the dashboard. Note the error if any. | Likely fails or polls badly: no event triggers, partial catalog support. Do not claim support. |
| Azure SQL / SQL Server | Try connecting. | Not supported: SQL Server is a stub. |
| Azure Database for MySQL | Connect as MySQL, make the four changes, time them. | Should work with the MySQL listener, polling every 60s. Unverified. |
| Azure Cosmos DB (Mongo API) | Connect as MongoDB, create and drop a collection and an index. | Unknown. Needs change stream support. |
| Google Bigtable | None. | Not a fit: no tables-and-columns schema to watch. |
| MongoDB Atlas | Connect as MongoDB, create and drop a collection and an index. | Should work if the cluster is a replica set (Atlas always is). Unverified. |
| Amazon RDS MySQL, Cloud SQL MySQL | Connect as MySQL, make the four changes, time them. | Should work, polling every 60s. Unverified. |

## When a result comes back

- **Pass:** change that provider's tag on the site from "testing" to live and state its real timing.
- **Fail:** keep it off the site. Copy the output into a GitHub issue so the cause can be fixed.
