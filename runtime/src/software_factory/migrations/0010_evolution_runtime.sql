-- Recursive product/program evolution and selection-quality RSI.

CREATE TABLE IF NOT EXISTS evolution_checkpoints_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    program_id TEXT,
    boundary_type TEXT NOT NULL CHECK (boundary_type IN ('work','block','checkpoint','terminal','cross_run','structural')),
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    state_fingerprint TEXT NOT NULL,
    material INTEGER NOT NULL CHECK (material IN (0,1)),
    observations_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    UNIQUE(mission_id,boundary_type,source_type,source_id,state_fingerprint)
);

CREATE TABLE IF NOT EXISTS program_change_candidates_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    program_id TEXT,
    checkpoint_id TEXT REFERENCES evolution_checkpoints_v2(id),
    change_kind TEXT NOT NULL CHECK (change_kind IN ('amend_current','successor','parallel_portfolio','split','merge','retire','replace')),
    author_session_id TEXT REFERENCES agent_sessions(id),
    rationale_json TEXT NOT NULL,
    change_spec_json TEXT NOT NULL,
    requested_range_root TEXT NOT NULL,
    accepted_history_root TEXT NOT NULL,
    currentness_root TEXT NOT NULL,
    candidate_root TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending','accepted','revise','rejected')),
    reviewer_session_id TEXT REFERENCES agent_sessions(id),
    review_evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    application_status TEXT NOT NULL DEFAULT 'pending' CHECK (application_status IN ('pending','applying','applied','failed','rolled_back')),
    application_result_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mission_id,candidate_root)
);

CREATE TABLE IF NOT EXISTS program_portfolios_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    parent_program_id TEXT,
    mode TEXT NOT NULL CHECK (mode IN ('sequential','parallel')),
    baseline_currentness_root TEXT NOT NULL,
    lanes_json TEXT NOT NULL,
    active_lane_ids_json TEXT NOT NULL DEFAULT '[]',
    completed_lane_ids_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','active','completed','failed','cancelled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS selection_records_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    selection_group TEXT NOT NULL,
    selection_type TEXT NOT NULL CHECK (selection_type IN ('feature','problem','design','architecture','strategy','program','experiment','policy')),
    candidate_key TEXT NOT NULL,
    proposer_session_id TEXT REFERENCES agent_sessions(id),
    selector_session_id TEXT REFERENCES agent_sessions(id),
    candidate_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    expected_value_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'considered' CHECK (status IN ('considered','challenged','selected','rejected','deferred','superseded')),
    rationale_json TEXT NOT NULL DEFAULT '{}',
    selected_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mission_id,selection_group,candidate_key)
);
CREATE INDEX IF NOT EXISTS idx_selection_records_group
    ON selection_records_v2(mission_id, selection_group, status);

CREATE TABLE IF NOT EXISTS selection_reviews_v2 (
    id TEXT PRIMARY KEY,
    selection_id TEXT NOT NULL REFERENCES selection_records_v2(id) ON DELETE CASCADE,
    reviewer_session_id TEXT REFERENCES agent_sessions(id),
    disposition TEXT NOT NULL CHECK (disposition IN ('accept','challenge','reject','defer')),
    findings_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    review_root TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(selection_id,review_root)
);

CREATE TABLE IF NOT EXISTS selection_outcomes_v2 (
    id TEXT PRIMARY KEY,
    selection_id TEXT NOT NULL REFERENCES selection_records_v2(id) ON DELETE CASCADE,
    outcome_type TEXT NOT NULL CHECK (outcome_type IN ('success','failure','mixed','unknown','counterfactual_limit')),
    metrics_json TEXT NOT NULL DEFAULT '{}',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    causal_confidence REAL NOT NULL CHECK (causal_confidence BETWEEN 0.0 AND 1.0),
    limitations_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS selector_policy_candidates_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    policy_json TEXT NOT NULL,
    policy_root TEXT NOT NULL,
    author_session_id TEXT REFERENCES agent_sessions(id),
    historical_status TEXT NOT NULL DEFAULT 'pending' CHECK (historical_status IN ('pending','passed','failed','inconclusive')),
    forward_status TEXT NOT NULL DEFAULT 'pending' CHECK (forward_status IN ('pending','passed','failed','inconclusive')),
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending','accepted','rejected','revise')),
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate','evaluating','active','rolled_back','rejected','superseded')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mission_id,policy_root)
);

CREATE TABLE IF NOT EXISTS selector_policy_evaluations_v2 (
    id TEXT PRIMARY KEY,
    policy_candidate_id TEXT NOT NULL REFERENCES selector_policy_candidates_v2(id) ON DELETE CASCADE,
    evaluation_type TEXT NOT NULL CHECK (evaluation_type IN ('historical','forward_shadow','independent_review','live_effectiveness')),
    disposition TEXT NOT NULL CHECK (disposition IN ('passed','failed','inconclusive','accepted','rejected','revise','effective','ineffective')),
    case_ids_json TEXT NOT NULL DEFAULT '[]',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    evaluator_session_id TEXT REFERENCES agent_sessions(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS active_selector_policies_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    policy_candidate_id TEXT NOT NULL REFERENCES selector_policy_candidates_v2(id),
    policy_root TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','rolled_back','superseded')),
    activated_at TEXT NOT NULL,
    deactivated_at TEXT,
    UNIQUE(mission_id,version)
);
