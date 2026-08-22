-- Schedules, reports, notifications/readback, and authenticated operator actions.

CREATE TABLE IF NOT EXISTS schedules_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT,
    schedule_type TEXT NOT NULL CHECK (schedule_type IN ('interval','at','event')),
    specification_json TEXT NOT NULL,
    action_json TEXT NOT NULL,
    next_run_at TEXT,
    last_run_at TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','completed','cancelled','failed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_schedules_v2_due
    ON schedules_v2(status,next_run_at);

CREATE TABLE IF NOT EXISTS reports_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT,
    report_type TEXT NOT NULL CHECK (report_type IN ('checkpoint','incident','terminal','cross_run','release','cleanup','factory_floor')),
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    content_root TEXT NOT NULL,
    json_content TEXT NOT NULL,
    markdown_content TEXT NOT NULL,
    pdf_path TEXT,
    status TEXT NOT NULL DEFAULT 'generated' CHECK (status IN ('generated','queued','delivered','read','failed','superseded')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(report_type,source_type,source_id,content_root)
);

CREATE TABLE IF NOT EXISTS notifications_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT,
    channel TEXT NOT NULL CHECK (channel IN ('file','email','smtp','webhook','stdout')),
    destination TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_text TEXT NOT NULL,
    attachment_paths_json TEXT NOT NULL DEFAULT '[]',
    dedupe_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sending','sent','delivered','read','retry','failed','cancelled')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    next_attempt_at TEXT,
    provider_message_id TEXT,
    readback_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notifications_v2_due
    ON notifications_v2(status,next_attempt_at);

CREATE TABLE IF NOT EXISTS notification_attempts_v2 (
    id TEXT PRIMARY KEY,
    notification_id TEXT NOT NULL REFERENCES notifications_v2(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    request_root TEXT NOT NULL,
    response_json TEXT,
    status TEXT NOT NULL CHECK (status IN ('sending','sent','failed','ambiguous')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE(notification_id,attempt_number)
);

CREATE TABLE IF NOT EXISTS operator_action_tokens_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT,
    token_hash TEXT NOT NULL UNIQUE,
    allowed_actions_json TEXT NOT NULL,
    scope_json TEXT NOT NULL DEFAULT '{}',
    expires_at TEXT NOT NULL,
    max_uses INTEGER NOT NULL DEFAULT 1,
    use_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','consumed','expired','revoked')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operator_decisions_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT,
    token_id TEXT NOT NULL REFERENCES operator_action_tokens_v2(id),
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    request_root TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'accepted' CHECK (status IN ('accepted','applied','rejected','failed')),
    result_json TEXT,
    created_at TEXT NOT NULL,
    applied_at TEXT,
    UNIQUE(token_id,request_root)
);
