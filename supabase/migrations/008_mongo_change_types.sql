-- Migration 008: change_type values the MongoDB listener writes
-- createCollection is recorded as collection_created, and anything the listener
-- doesn't recognise as schema_change. Neither was in the enum, so those events
-- were rejected by the database and lost. Safe to re-run.
-- Only needed on a database created before this was added to supabase/schema.sql.

alter type change_type add value if not exists 'collection_created';
alter type change_type add value if not exists 'schema_change';
