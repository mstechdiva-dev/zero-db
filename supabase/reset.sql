-- SchemaZero — reset (DESTRUCTIVE)
--
-- Use this only when your database has tables from an older or different
-- schema and you want to start clean before running supabase/schema.sql.
--
-- It DELETES: organizations, users, connected databases (including saved
-- connection strings), change events, impact analyses, alert settings,
-- notification logs, Scout heartbeats and the older schema_snapshots table.
--
-- It KEEPS: your login accounts (auth.users), the waitlist, sales leads, and
-- prompts saved from the admin panel (agent_skills).
--
-- After it runs, run supabase/schema.sql. That file also re-creates an
-- organization for every login account that already exists.

drop trigger if exists on_auth_user_created on auth.users;

drop table if exists notification_log   cascade;
drop table if exists impact_analysis    cascade;
drop table if exists change_events      cascade;
drop table if exists scout_heartbeat    cascade;
drop table if exists schema_snapshots   cascade;
drop table if exists alert_configs      cascade;
drop table if exists connected_databases cascade;
drop table if exists users              cascade;
drop table if exists organizations      cascade;

drop function if exists handle_new_user() cascade;
drop function if exists set_updated_at() cascade;

drop type if exists notification_status cascade;
drop type if exists alert_channel       cascade;
drop type if exists risk_level          cascade;
drop type if exists change_type         cascade;
drop type if exists db_engine           cascade;
drop type if exists user_role           cascade;
drop type if exists plan_type           cascade;
