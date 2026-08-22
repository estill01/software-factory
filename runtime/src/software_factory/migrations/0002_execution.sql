CREATE TABLE IF NOT EXISTS agent_sessions (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE SET NULL,
    provider TEXT NOT NULL,
    external_thread_id TEXT,
    external_task_id TEXT,
    role TEXT NOT NULL,
    model TEXT,
    reasoning_level TEXT,
    parent_session_id TEXT REFERENCES agent_sessions(id),
    loaded_release_id TEXT,
    loaded_instruction_root TEXT,
    desired_status TEXT NOT NULL CHECK(desired_status IN ('running','idle','stopping','stopped')),
    observed_status TEXT NOT NULL CHECK(observed_status IN (
        'starting','active','idle','unresponsive','stopped','lost'
    )),
    last_heartbeat_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT NOT NULL,
    stopped_at TEXT
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    workspace_type TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    branch TEXT,
    base_revision TEXT NOT NULL,
    current_revision TEXT,
    owner_assignment_id TEXT,
    writable_scope_json TEXT NOT NULL DEFAULT '[]',
    exclusions_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL CHECK(status IN (
        'creating','ready','active','frozen','retained','retired','failed'
    )),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_assignments (
    id TEXT PRIMARY KEY,
    work_item_id TEXT NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
    agent_session_id TEXT NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    workspace_id TEXT REFERENCES workspaces(id),
    role TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'offered','accepted','active','completed','released','revoked','expired'
    )),
    assigned_by_execution_id TEXT,
    assignment_scope_json TEXT NOT NULL DEFAULT '{}',
    instructions_root TEXT,
    lease_generation INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    released_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS one_active_implementer
ON work_assignments(work_item_id)
WHERE role='implementer' AND status IN ('accepted','active');

CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    obligation_id TEXT REFERENCES obligations(id),
    primary_hypothesis_id TEXT,
    origin_execution_id TEXT,
    experiment_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'proposed','designing','ready','running','analyzing','concluded','invalidated','cancelled'
    )),
    question TEXT NOT NULL,
    design_json TEXT NOT NULL,
    arms_json TEXT NOT NULL DEFAULT '[]',
    measurements_json TEXT NOT NULL DEFAULT '[]',
    success_conditions_json TEXT NOT NULL DEFAULT '{}',
    failure_conditions_json TEXT NOT NULL DEFAULT '{}',
    inconclusive_conditions_json TEXT NOT NULL DEFAULT '{}',
    stop_conditions_json TEXT NOT NULL DEFAULT '{}',
    budget_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    conclusion TEXT,
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    obligation_id TEXT REFERENCES obligations(id),
    work_item_id TEXT REFERENCES work_items(id),
    experiment_id TEXT REFERENCES experiments(id),
    agent_session_id TEXT REFERENCES agent_sessions(id),
    assignment_id TEXT REFERENCES work_assignments(id),
    execution_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'queued','dispatching','leased','running','verifying',
        'succeeded','failed','abandoned','cancelled','invalidated'
    )),
    strategy_key TEXT,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    idempotency_key TEXT NOT NULL UNIQUE,
    lease_generation INTEGER NOT NULL DEFAULT 0,
    input_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    limits_json TEXT NOT NULL DEFAULT '{}',
    usage_json TEXT NOT NULL DEFAULT '{}',
    source_revision_before TEXT,
    source_revision_after TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leases (
    id TEXT PRIMARY KEY,
    resource_key TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('read','write','exclusive')),
    owner_execution_id TEXT REFERENCES executions(id) ON DELETE CASCADE,
    owner_assignment_id TEXT REFERENCES work_assignments(id) ON DELETE CASCADE,
    generation INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','released','expired','revoked')),
    expires_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    released_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS one_active_exclusive_lease
ON leases(resource_key)
WHERE status='active' AND mode IN ('write','exclusive');

CREATE TABLE IF NOT EXISTS qa_requirements (
    id TEXT PRIMARY KEY,
    work_item_id TEXT NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
    phase TEXT NOT NULL CHECK(phase IN ('candidate','integrated','installed','terminal')),
    qa_type TEXT NOT NULL,
    required INTEGER NOT NULL CHECK(required IN (0,1)),
    independence_role TEXT,
    command_json TEXT NOT NULL DEFAULT '{}',
    predicate_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK(status IN ('pending','running','passed','failed','stale','waived')),
    candidate_revision TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS qa_results (
    id TEXT PRIMARY KEY,
    requirement_id TEXT NOT NULL REFERENCES qa_requirements(id) ON DELETE CASCADE,
    execution_id TEXT REFERENCES executions(id),
    status TEXT NOT NULL CHECK(status IN ('passed','failed','invalid','inconclusive')),
    revision TEXT NOT NULL,
    evidence_id TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    reviewer_session_id TEXT REFERENCES agent_sessions(id),
    observed_at TEXT NOT NULL,
    stale_at TEXT
);
