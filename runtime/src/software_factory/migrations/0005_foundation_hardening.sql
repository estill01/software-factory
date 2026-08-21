ALTER TABLE commands ADD COLUMN command_root TEXT;
ALTER TABLE commands ADD COLUMN requested_scope_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE commands ADD COLUMN mission_id TEXT REFERENCES missions(id);
ALTER TABLE authority_records ADD COLUMN uses_remaining INTEGER;
ALTER TABLE authority_records ADD COLUMN consumed_at TEXT;
ALTER TABLE program_revisions ADD COLUMN revision_root TEXT;
ALTER TABLE program_revisions ADD COLUMN review_root TEXT;

CREATE TABLE IF NOT EXISTS evidence_records (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    revision TEXT,
    status TEXT NOT NULL CHECK(status IN ('current','stale','failed','invalidated')),
    artifact_id TEXT REFERENCES artifacts(id),
    execution_id TEXT REFERENCES executions(id),
    producer_session_id TEXT REFERENCES agent_sessions(id),
    payload_json TEXT NOT NULL DEFAULT '{}',
    root_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    invalidated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_evidence_subject
ON evidence_records(subject_type, subject_id, status, created_at);

CREATE INDEX IF NOT EXISTS idx_commands_mission
ON commands(mission_id, created_at);
