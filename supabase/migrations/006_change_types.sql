-- Migration 006: change_type values Scout actually writes
-- Scout emits table_created, index_created, key_type_changed and
-- ttl_policy_changed. The original enum only had *_added / ttl_changed, so
-- those events were rejected by the database and silently lost.
-- Run each statement as-is in the Supabase SQL editor. Safe to re-run.

alter type change_type add value if not exists 'table_created';
alter type change_type add value if not exists 'index_created';
alter type change_type add value if not exists 'key_type_changed';
alter type change_type add value if not exists 'ttl_policy_changed';
