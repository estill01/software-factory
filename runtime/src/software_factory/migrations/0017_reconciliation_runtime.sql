-- Accepted-work integration and unfinished-work restart effects.

CREATE TABLE IF NOT EXISTS integration_candidates_v2 (
    id TEXT PRIMARY KEY,
    cleanup_item_id TEXT NOT NULL REFERENCES cleanup_items_v2(id) ON DELETE CASCADE,
    preservation_bundle_id TEXT NOT NULL REFERENCES preservation_bundles_v2(id),
    repository_root TEXT NOT NULL,
    source_branch TEXT NOT NULL,
    source_head TEXT NOT NULL,
    target_branch TEXT NOT NULL,
    target_head_before TEXT NOT NULL,
    integration_branch TEXT NOT NULL,
    integration_worktree TEXT NOT NULL,
    candidate_head TEXT,
    validation_command_json TEXT NOT NULL DEFAULT '[]',
    validation_result_json TEXT,
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','merging','validating','accepted','published','failed','rolled_back')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE(cleanup_item_id,source_head,target_head_before)
);

CREATE TABLE IF NOT EXISTS restart_workspaces_v2 (
    id TEXT PRIMARY KEY,
    cleanup_item_id TEXT NOT NULL REFERENCES cleanup_items_v2(id) ON DELETE CASCADE,
    preservation_bundle_id TEXT NOT NULL REFERENCES preservation_bundles_v2(id),
    repository_root TEXT NOT NULL,
    baseline_branch TEXT NOT NULL,
    baseline_head TEXT NOT NULL,
    restart_branch TEXT NOT NULL UNIQUE,
    restart_worktree TEXT NOT NULL UNIQUE,
    restored_source_reference TEXT,
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','creating','ready','assigned','completed','failed','retired')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);
