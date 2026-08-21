ALTER TABLE supervision_assignments ADD COLUMN material_fingerprint TEXT;
ALTER TABLE supervision_assignments ADD COLUMN last_result_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE supervision_assignments ADD COLUMN state_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE supervision_assignments ADD COLUMN check_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE incidents ADD COLUMN failure_fingerprint TEXT;
ALTER TABLE incidents ADD COLUMN strategy_key TEXT;
ALTER TABLE incidents ADD COLUMN occurrence_count INTEGER NOT NULL DEFAULT 1;
ALTER TABLE incidents ADD COLUMN verification_due_at TEXT;
ALTER TABLE incidents ADD COLUMN parent_incident_id TEXT REFERENCES incidents(id);
ALTER TABLE incidents ADD COLUMN dedup_key TEXT;
ALTER TABLE incidents ADD COLUMN correction_work_item_id TEXT REFERENCES work_items(id);
ALTER TABLE incidents ADD COLUMN verification_execution_id TEXT REFERENCES executions(id);
ALTER TABLE incidents ADD COLUMN source_execution_id TEXT REFERENCES executions(id);

ALTER TABLE work_items ADD COLUMN strategy_key TEXT;
ALTER TABLE work_items ADD COLUMN strategy_revision INTEGER NOT NULL DEFAULT 1;

CREATE TABLE supervision_checks (
    id TEXT PRIMARY KEY,
    assignment_id TEXT NOT NULL REFERENCES supervision_assignments(id) ON DELETE CASCADE,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    target_fingerprint TEXT NOT NULL,
    material_changed INTEGER NOT NULL CHECK(material_changed IN (0,1)),
    status TEXT NOT NULL CHECK(status IN ('no_change','clear','finding','failed')),
    findings_json TEXT NOT NULL DEFAULT '[]',
    execution_id TEXT REFERENCES executions(id),
    reviewer_session_id TEXT REFERENCES agent_sessions(id),
    created_at TEXT NOT NULL
);

CREATE TABLE strategy_outcomes (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    work_item_id TEXT REFERENCES work_items(id) ON DELETE SET NULL,
    execution_id TEXT NOT NULL UNIQUE REFERENCES executions(id) ON DELETE CASCADE,
    obligation_id TEXT REFERENCES obligations(id) ON DELETE SET NULL,
    problem_key TEXT NOT NULL,
    strategy_key TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK(outcome IN (
        'succeeded','failed','abandoned','cancelled','unexpected_success'
    )),
    failure_fingerprint TEXT,
    evidence_root TEXT,
    capability_delta_json TEXT NOT NULL DEFAULT '{}',
    resource_use_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE adaptive_actions (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    incident_id TEXT REFERENCES incidents(id) ON DELETE SET NULL,
    source_execution_id TEXT REFERENCES executions(id) ON DELETE SET NULL,
    action_kind TEXT NOT NULL CHECK(action_kind IN (
        'diagnose','reflect','inline_correction','alternative_strategy',
        'candidate_comparison','architecture_review','program_review',
        'success_generalization','contain','resume_safe_frontier'
    )),
    causal_level TEXT NOT NULL,
    problem_key TEXT NOT NULL,
    prior_strategy_key TEXT,
    selected_work_item_id TEXT REFERENCES work_items(id),
    status TEXT NOT NULL CHECK(status IN (
        'proposed','selected','running','effective','ineffective','retired'
    )),
    rationale_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX one_active_adaptive_action_per_problem
ON adaptive_actions(mission_id, problem_key, action_kind)
WHERE status IN ('proposed','selected','running');

CREATE UNIQUE INDEX one_active_supervision_role_per_target
ON supervision_assignments(mission_id, role, target_type, target_id)
WHERE status='active';

CREATE UNIQUE INDEX one_open_incident_per_dedup_key
ON incidents(dedup_key)
WHERE dedup_key IS NOT NULL AND status NOT IN ('resolved','superseded');

CREATE INDEX idx_supervision_due
ON supervision_assignments(status,next_due_at,last_checked_at);

CREATE INDEX idx_incident_fingerprint
ON incidents(mission_id,failure_fingerprint,strategy_key,status);

CREATE INDEX idx_strategy_problem
ON strategy_outcomes(mission_id,problem_key,strategy_key,outcome,created_at);

CREATE INDEX idx_executions_strategy_outcome
ON executions(mission_id,work_item_id,strategy_key,status,failure_fingerprint);
