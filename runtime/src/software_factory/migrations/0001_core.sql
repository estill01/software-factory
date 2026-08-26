PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repositories (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    path TEXT NOT NULL UNIQUE,
    remote_url TEXT,
    default_branch TEXT,
    current_revision TEXT,
    workspace_policy_json TEXT NOT NULL DEFAULT '{}',
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS missions (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'active','waiting_reserved_input','terminal_verification',
        'completed','cancelled_by_authority'
    )),
    autonomy_mode TEXT NOT NULL CHECK(autonomy_mode IN (
        'fixed','recommend','reviewed_autonomous','full_autonomous'
    )),
    authority_root TEXT,
    resource_limits_json TEXT NOT NULL DEFAULT '{}',
    terminal_evidence_id TEXT,
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS authority_records (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    effect_classes_json TEXT NOT NULL,
    scope_json TEXT NOT NULL,
    parent_id TEXT REFERENCES authority_records(id),
    status TEXT NOT NULL CHECK(status IN ('active','expired','superseded','revoked')),
    expires_at TEXT,
    root_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS capabilities (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    parent_id TEXT REFERENCES capabilities(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    required INTEGER NOT NULL CHECK(required IN (0,1)),
    protected INTEGER NOT NULL CHECK(protected IN (0,1)),
    status TEXT NOT NULL CHECK(status IN (
        'absent','partial','locally_verified','integrated','end_to_end_verified','regressed'
    )),
    acceptance_spec_json TEXT NOT NULL DEFAULT '{}',
    current_evidence_id TEXT,
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS obligations (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    capability_id TEXT REFERENCES capabilities(id),
    parent_id TEXT REFERENCES obligations(id),
    obligation_type TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'open','ready','in_progress','waiting_for_evidence','blocked_reserved',
        'satisfied','superseded','waived_by_authority'
    )),
    priority INTEGER NOT NULL DEFAULT 0,
    blocked_reason TEXT,
    revisit_after TEXT,
    resolution_json TEXT NOT NULL DEFAULT '{}',
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS obligation_dependencies (
    obligation_id TEXT NOT NULL REFERENCES obligations(id) ON DELETE CASCADE,
    depends_on_id TEXT NOT NULL REFERENCES obligations(id) ON DELETE CASCADE,
    condition_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY(obligation_id, depends_on_id),
    CHECK(obligation_id <> depends_on_id)
);

CREATE TABLE IF NOT EXISTS programs (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('draft','active','superseded','completed','cancelled')),
    current_revision_id TEXT,
    requested_range_json TEXT NOT NULL DEFAULT '{}',
    terminal_criteria_json TEXT NOT NULL DEFAULT '{}',
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS program_revisions (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    parent_id TEXT REFERENCES program_revisions(id),
    source_ref TEXT,
    mapping_json TEXT NOT NULL DEFAULT '{}',
    graph_json TEXT NOT NULL DEFAULT '{}',
    accepted_history_json TEXT NOT NULL DEFAULT '{}',
    resume_frontier_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK(status IN ('proposed','under_review','accepted','rejected','superseded')),
    author_execution_id TEXT,
    review_execution_id TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(program_id, sequence)
);

CREATE TABLE IF NOT EXISTS work_items (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    program_id TEXT REFERENCES programs(id),
    program_revision_id TEXT REFERENCES program_revisions(id),
    obligation_id TEXT REFERENCES obligations(id),
    parent_id TEXT REFERENCES work_items(id),
    work_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    planning_status TEXT NOT NULL CHECK(planning_status IN (
        'proposed','selected','rejected','deferred','superseded'
    )),
    execution_status TEXT NOT NULL CHECK(execution_status IN (
        'not_started','queued','running','submitted','failed','abandoned','cancelled','verified'
    )),
    qa_status TEXT NOT NULL CHECK(qa_status IN (
        'not_started','pending','running','changes_requested','passed','failed','stale'
    )),
    acceptance_status TEXT NOT NULL CHECK(acceptance_status IN (
        'pending','candidate_accepted','integrated_accepted','installed_accepted',
        'rejected','regressed'
    )),
    priority INTEGER NOT NULL DEFAULT 0,
    proposed_by TEXT,
    selected_by TEXT,
    selection_policy_id TEXT,
    selection_basis_json TEXT NOT NULL DEFAULT '{}',
    expected_effect_json TEXT NOT NULL DEFAULT '{}',
    acceptance_spec_json TEXT NOT NULL DEFAULT '{}',
    writable_scope_json TEXT NOT NULL DEFAULT '[]',
    lane_key TEXT,
    candidate_revision TEXT,
    integrated_revision TEXT,
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_dependencies (
    work_item_id TEXT NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
    depends_on_id TEXT NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
    condition_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY(work_item_id, depends_on_id),
    CHECK(work_item_id <> depends_on_id)
);
