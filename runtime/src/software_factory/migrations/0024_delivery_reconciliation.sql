-- Durable release-transition and interrupted repository-effect reconciliation.

CREATE TABLE IF NOT EXISTS release_transitions_v2 (
    id TEXT PRIMARY KEY,
    transition_root TEXT NOT NULL UNIQUE,
    transition_type TEXT NOT NULL CHECK (transition_type IN ('activate','rollback')),
    release_id TEXT NOT NULL REFERENCES immutable_releases_v2(id) ON DELETE CASCADE,
    target_release_id TEXT REFERENCES immutable_releases_v2(id),
    previous_release_id TEXT REFERENCES immutable_releases_v2(id),
    release_root TEXT NOT NULL,
    pointer_payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'prepared'
        CHECK (status IN ('prepared','pointer_written','committed','failed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_release_transitions_release
    ON release_transitions_v2(release_id,transition_type,status);

CREATE UNIQUE INDEX IF NOT EXISTS idx_restart_workspace_exact_source
    ON restart_workspaces_v2(cleanup_item_id,baseline_head);
