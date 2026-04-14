-- Agent skills: source of truth for agent MD content.
-- The admin panel writes here; FastAPI reads here on each agent call.
-- Git remains the version history — no separate versions table needed.

CREATE TABLE IF NOT EXISTS agent_skills (
    name        TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    saved_by    TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Service role bypasses RLS; deny direct browser access.
ALTER TABLE agent_skills ENABLE ROW LEVEL SECURITY;

CREATE POLICY "deny_all" ON agent_skills
    FOR ALL TO authenticated, anon
    USING (false);
