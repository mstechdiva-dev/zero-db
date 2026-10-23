-- Migration 009: remember which trial reminder email an org has had
-- 0 = none sent, 1 = "3 days left" sent, 2 = "trial ended" sent.
-- Without it the backend would send the same reminder every hour.
-- Safe to re-run. Only needed on a database created before this was added to supabase/schema.sql.

alter table organizations
  add column if not exists trial_reminder_stage smallint not null default 0;
