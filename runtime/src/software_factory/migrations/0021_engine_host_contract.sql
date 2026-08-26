CREATE TABLE IF NOT EXISTS engine_submissions_v2 (
    idempotency_key TEXT PRIMARY KEY,
    request_root TEXT NOT NULL,
    mission_id TEXT NOT NULL UNIQUE REFERENCES missions(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_engine_submissions_mission
ON engine_submissions_v2(mission_id);
