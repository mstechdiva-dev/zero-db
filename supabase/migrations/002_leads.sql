-- Migration 002: Add leads table
-- Stores qualified sales leads captured by the Sal agent (CREATE_LEAD signal).
-- This is an admin-only table — regular users cannot read or write it.
-- The backend uses the service-role key to insert records, bypassing RLS.

CREATE TABLE IF NOT EXISTS leads (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id           UUID        REFERENCES organizations(id) ON DELETE SET NULL,
  user_email       TEXT,
  conversation     JSONB       NOT NULL DEFAULT '[]',
  sal_summary      TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS leads_org_id_idx     ON leads(org_id);
CREATE INDEX IF NOT EXISTS leads_created_at_idx ON leads(created_at DESC);

-- Enable RLS — no user-facing policies are added, so only the service-role
-- key (used by the FastAPI backend and Next.js server components) can access
-- this table. Regular anon/authenticated Supabase keys cannot.
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE leads IS
  'Qualified sales leads flagged by the Sal agent. Admin-only — no RLS policies '
  'for regular users. Access via service-role key only.';
