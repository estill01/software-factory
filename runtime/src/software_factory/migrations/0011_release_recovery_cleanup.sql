-- Immutable release, systemic recovery, and no-loss repository reconciliation.

CREATE TABLE IF NOT EXISTS immutable_releases_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT,
    source_revision TEXT NOT NULL,
    source_tree_root TEXT NOT NULL,
    manifest_root TEXT NOT NULL,
    release_path TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    implementer_session_id TEXT,
    reviewer_session_id TEXT,
    evaluator_session_id TEXT,
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending','accepted','rejected','revise')),
    verification_status TEXT NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending','passed','failed')),
    status TEXT NOT NULL DEFAULT 'staged' CHECK (status IN ('staged','accepted','active','superseded','rolled_back','rejected','failed')),
    previous_release_id TEXT REFERENCES immutable_releases_v2(id),
    staged_at TEXT NOT NULL,
    activated_at TEXT,
    deactivated_at TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE(source_revision,manifest_root)
);

CREATE TABLE IF NOT EXISTS release_reviews_v2 (
    id TEXT PRIMARY KEY,
    release_id TEXT NOT NULL REFERENCES immutable_releases_v2(id) ON DELETE CASCADE,
    reviewer_session_id TEXT NOT NULL,
    disposition TEXT NOT NULL CHECK (disposition IN ('accepted','rejected','revise')),
    findings_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    review_root TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(release_id,review_root)
);

CREATE TABLE IF NOT EXISTS release_verifications_v2 (
    id TEXT PRIMARY KEY,
    release_id TEXT NOT NULL REFERENCES immutable_releases_v2(id) ON DELETE CASCADE,
    verification_type TEXT NOT NULL CHECK (verification_type IN ('fresh_process','installed','health','agent_refresh','rollback')),
    command_json TEXT,
    exit_code INTEGER,
    stdout_text TEXT,
    stderr_text TEXT,
    evidence_root TEXT NOT NULL,
    disposition TEXT NOT NULL CHECK (disposition IN ('passed','failed','inconclusive')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS release_agent_refreshes_v2 (
    id TEXT PRIMARY KEY,
    release_id TEXT NOT NULL REFERENCES immutable_releases_v2(id) ON DELETE CASCADE,
    agent_session_id TEXT NOT NULL,
    boundary_type TEXT NOT NULL,
    prior_revision TEXT,
    target_revision TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','ready','refreshed','failed','deferred')),
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(release_id,agent_session_id)
);

CREATE TABLE IF NOT EXISTS factory_recovery_cases_v2 (
    id TEXT PRIMARY KEY,
    target_mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    defect_class TEXT NOT NULL,
    defect_fingerprint TEXT NOT NULL,
    target_state_json TEXT NOT NULL,
    requested_range_root TEXT NOT NULL,
    tracker_currentness_root TEXT NOT NULL,
    safe_frontier_json TEXT NOT NULL DEFAULT '[]',
    repair_revision TEXT,
    repair_evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    release_id TEXT REFERENCES immutable_releases_v2(id),
    status TEXT NOT NULL DEFAULT 'detected' CHECK (status IN ('detected','repairing','qa','releasing','restoring','resuming','verifying','resolved','failed')),
    resume_count INTEGER NOT NULL DEFAULT 0,
    opened_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    UNIQUE(target_mission_id,defect_fingerprint,status)
);

CREATE TABLE IF NOT EXISTS recovery_resume_tokens_v2 (
    id TEXT PRIMARY KEY,
    recovery_id TEXT NOT NULL REFERENCES factory_recovery_cases_v2(id) ON DELETE CASCADE,
    target_mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    resume_key TEXT NOT NULL UNIQUE,
    wake_payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'reserved' CHECK (status IN ('reserved','sent','acknowledged','expired','cancelled')),
    reserved_at TEXT NOT NULL,
    sent_at TEXT,
    acknowledged_at TEXT,
    UNIQUE(recovery_id)
);

CREATE TABLE IF NOT EXISTS repository_inventories_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT,
    repository_root TEXT NOT NULL,
    repository_head TEXT,
    inventory_root TEXT NOT NULL,
    branches_json TEXT NOT NULL DEFAULT '[]',
    worktrees_json TEXT NOT NULL DEFAULT '[]',
    stashes_json TEXT NOT NULL DEFAULT '[]',
    status_json TEXT NOT NULL DEFAULT '{}',
    detached_commits_json TEXT NOT NULL DEFAULT '[]',
    active_writers_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS preservation_bundles_v2 (
    id TEXT PRIMARY KEY,
    inventory_id TEXT NOT NULL REFERENCES repository_inventories_v2(id) ON DELETE CASCADE,
    bundle_path TEXT NOT NULL,
    bundle_root TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (0,1)),
    created_at TEXT NOT NULL,
    verified_at TEXT,
    UNIQUE(inventory_id,bundle_root)
);

CREATE TABLE IF NOT EXISTS cleanup_items_v2 (
    id TEXT PRIMARY KEY,
    inventory_id TEXT NOT NULL REFERENCES repository_inventories_v2(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL CHECK (item_type IN ('branch','worktree','stash','dirty_file','untracked_file','detached_commit','task_owner')),
    item_key TEXT NOT NULL,
    classification TEXT NOT NULL DEFAULT 'unknown' CHECK (classification IN ('active','accepted','unfinished','redundant','historical','unknown','protected')),
    disposition TEXT NOT NULL DEFAULT 'retain' CHECK (disposition IN ('retain','preserve','integrate','retire','restart','defer')),
    evidence_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','running','completed','failed','cancelled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(inventory_id,item_type,item_key)
);

CREATE TABLE IF NOT EXISTS cleanup_effects_v2 (
    id TEXT PRIMARY KEY,
    cleanup_item_id TEXT NOT NULL REFERENCES cleanup_items_v2(id) ON DELETE CASCADE,
    effect_type TEXT NOT NULL,
    precondition_json TEXT NOT NULL,
    result_json TEXT,
    rollback_json TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','succeeded','failed','rolled_back')),
    started_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);
