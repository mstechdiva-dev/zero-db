-- Agent skill version history
-- Stores every save of an agent MD file so edits can be rolled back.

CREATE TABLE IF NOT EXISTS agent_skill_versions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name  TEXT        NOT NULL,
    content     TEXT        NOT NULL,
    saved_by    TEXT,                       -- admin email
    label       TEXT,                       -- optional human note (e.g. "Reverted to 2026-04-01")
    saved_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agent_skill_versions_agent_name_saved_at
    ON agent_skill_versions (agent_name, saved_at DESC);

-- Only service role can access this table — no customer RLS needed
ALTER TABLE agent_skill_versions ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS, so no policy is needed for backend access.
-- Deny all access to authenticated / anon roles for safety.
CREATE POLICY "deny_all" ON agent_skill_versions
    FOR ALL TO authenticated, anon
    USING (false);
