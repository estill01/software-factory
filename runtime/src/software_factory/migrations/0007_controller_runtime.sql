ALTER TABLE work_items ADD COLUMN repository_id TEXT REFERENCES repositories(id);
ALTER TABLE work_items ADD COLUMN required_role TEXT NOT NULL DEFAULT 'implementer';
ALTER TABLE work_items ADD COLUMN provider_key TEXT;

ALTER TABLE executions ADD COLUMN provider_key TEXT;
ALTER TABLE executions ADD COLUMN provider_handle_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE executions ADD COLUMN dispatch_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE executions ADD COLUMN last_provider_poll_at TEXT;

CREATE TABLE IF NOT EXISTS provider_callbacks (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL UNIQUE REFERENCES executions(id) ON DELETE CASCADE,
    generation INTEGER NOT NULL,
    token_sha256 TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','used','revoked','expired')),
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    used_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS one_active_execution_per_work
ON executions(work_item_id)
WHERE work_item_id IS NOT NULL
  AND status IN ('queued','dispatching','leased','running','verifying');

CREATE UNIQUE INDEX IF NOT EXISTS one_active_assignment_per_agent
ON work_assignments(agent_session_id)
WHERE status IN ('offered','accepted','active');

CREATE UNIQUE INDEX IF NOT EXISTS one_live_workspace_per_work
ON workspaces(work_item_id)
WHERE work_item_id IS NOT NULL
  AND workspace_type IN ('primary','cooperative_lane','candidate_lane')
  AND status IN ('creating','ready','active','frozen','retained');

CREATE INDEX IF NOT EXISTS idx_provider_executions
ON executions(provider_key,status,last_provider_poll_at);
