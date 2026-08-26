CREATE TABLE IF NOT EXISTS releases (
    id TEXT PRIMARY KEY,
    source_revision TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('candidate','staged','active','healthy','failed','rolled_back','retained')),
    previous_release_id TEXT REFERENCES releases(id),
    reviewer_session_id TEXT REFERENCES agent_sessions(id),
    evaluator_session_id TEXT REFERENCES agent_sessions(id),
    activated_at TEXT,
    verified_at TEXT,
    health_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recovery_cases (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    incident_id TEXT REFERENCES incidents(id),
    status TEXT NOT NULL CHECK(status IN (
        'detected','preserved','repairing','reviewing','releasing','restoring',
        'waking','verifying','resolved','failed'
    )),
    target_session_id TEXT REFERENCES agent_sessions(id),
    preserved_frontier_json TEXT NOT NULL,
    repair_work_item_id TEXT REFERENCES work_items(id),
    release_id TEXT REFERENCES releases(id),
    wake_idempotency_key TEXT UNIQUE,
    wake_count INTEGER NOT NULL DEFAULT 0,
    effectiveness_json TEXT NOT NULL DEFAULT '{}',
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cleanup_runs (
    id TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    execution_id TEXT REFERENCES executions(id),
    status TEXT NOT NULL CHECK(status IN (
        'inventory','preserving','integrating','validating','publishing',
        'retiring','restarting','completed','failed','rolled_back'
    )),
    inventory_json TEXT NOT NULL DEFAULT '{}',
    preservation_json TEXT NOT NULL DEFAULT '{}',
    integration_json TEXT NOT NULL DEFAULT '{}',
    retirement_json TEXT NOT NULL DEFAULT '{}',
    restart_json TEXT NOT NULL DEFAULT '{}',
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    schedule_type TEXT NOT NULL,
    spec_json TEXT NOT NULL,
    command_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','paused','completed','cancelled')),
    next_due_at TEXT,
    last_execution_id TEXT REFERENCES executions(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    execution_id TEXT REFERENCES executions(id),
    provider TEXT NOT NULL,
    channel_ref TEXT,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'queued','sending','delivered','readback_verified','failed','cancelled'
    )),
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    provider_result_json TEXT NOT NULL DEFAULT '{}',
    attachment_ids_json TEXT NOT NULL DEFAULT '[]',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,
    delivered_at TEXT,
    readback_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    producer_execution_id TEXT REFERENCES executions(id),
    sha256 TEXT NOT NULL,
    byte_count INTEGER NOT NULL,
    media_type TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(sha256, byte_count)
);

CREATE TABLE IF NOT EXISTS commands (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    actor_id TEXT,
    authority_record_id TEXT REFERENCES authority_records(id),
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    expected_version INTEGER,
    effect_class TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL CHECK(status IN ('running','succeeded','failed')),
    result_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    project_id TEXT REFERENCES projects(id),
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    stream_key TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source_type TEXT,
    source_id TEXT,
    subject_type TEXT,
    subject_id TEXT,
    causation_id TEXT,
    correlation_id TEXT,
    prior_version INTEGER,
    new_version INTEGER,
    payload_json TEXT NOT NULL,
    previous_hash TEXT,
    event_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_mission_sequence ON events(mission_id, sequence);
CREATE INDEX IF NOT EXISTS idx_events_stream_sequence ON events(stream_key, sequence);
CREATE INDEX IF NOT EXISTS idx_work_ready ON work_items(mission_id, planning_status, execution_status, priority);
CREATE INDEX IF NOT EXISTS idx_obligations_open ON obligations(mission_id, status, priority);
CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status, created_at);
CREATE INDEX IF NOT EXISTS idx_leases_expiry ON leases(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_classifications_subject ON classifications(subject_type, subject_id, created_at);
