ALTER TABLE acceptance_runs ADD COLUMN runner_id TEXT;
ALTER TABLE acceptance_runs ADD COLUMN claim_token TEXT;
ALTER TABLE acceptance_runs ADD COLUMN lease_expires_at TEXT;
ALTER TABLE acceptance_runs ADD COLUMN heartbeat_at TEXT;
ALTER TABLE acceptance_runs ADD COLUMN attempt_number INTEGER NOT NULL DEFAULT 0;
ALTER TABLE acceptance_runs ADD COLUMN last_error_json TEXT;

CREATE INDEX IF NOT EXISTS idx_acceptance_runs_active_lease
ON acceptance_runs(status, lease_expires_at, source_revision);
