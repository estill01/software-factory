-- Native supervision, adaptive correction, and retained success/failure cases.

CREATE TABLE IF NOT EXISTS supervision_monitors (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL CHECK (target_type IN ('mission','program','work_item','execution','release','factory')),
    target_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('watcher','semantic_reviewer','escalation_reviewer','fix_executor','effectiveness_reviewer','notice_reviewer')),
    agent_session_id TEXT REFERENCES agent_sessions(id),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','completed','cancelled')),
    policy_json TEXT NOT NULL DEFAULT '{}',
    last_fingerprint TEXT,
    last_observed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mission_id,target_type,target_id,role)
);

CREATE TABLE IF NOT EXISTS supervision_observations (
    id TEXT PRIMARY KEY,
    monitor_id TEXT NOT NULL REFERENCES supervision_monitors(id) ON DELETE CASCADE,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    fingerprint TEXT NOT NULL,
    material INTEGER NOT NULL CHECK (material IN (0,1)),
    classification TEXT NOT NULL CHECK (classification IN ('neutral','progress','failure','success','mixed','opportunity')),
    state_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_supervision_observations_monitor_created
    ON supervision_observations(monitor_id, created_at);

CREATE TABLE IF NOT EXISTS supervision_incidents (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    observation_id TEXT REFERENCES supervision_observations(id),
    incident_fingerprint TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('info','low','medium','high','critical')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','contained','correcting','verifying','resolved','accepted_risk','superseded')),
    causal_level INTEGER NOT NULL DEFAULT 0 CHECK (causal_level BETWEEN 0 AND 6),
    recurrence_count INTEGER NOT NULL DEFAULT 0,
    mechanism_json TEXT NOT NULL,
    trigger_json TEXT NOT NULL,
    effect_json TEXT NOT NULL,
    detection_json TEXT NOT NULL,
    containment_json TEXT NOT NULL,
    correction_json TEXT NOT NULL,
    recurrence_json TEXT NOT NULL,
    human_scheduling_leakage_json TEXT NOT NULL,
    affected_scope_json TEXT NOT NULL DEFAULT '[]',
    opened_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    UNIQUE(mission_id, incident_fingerprint, status)
);
CREATE INDEX IF NOT EXISTS idx_supervision_incidents_mission_status
    ON supervision_incidents(mission_id, status, severity);

CREATE TABLE IF NOT EXISTS supervision_actions (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES supervision_incidents(id) ON DELETE CASCADE,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN ('contain','local_repair','alternate_implementation','candidate_comparison','architecture_change','program_revision','selection_reconsideration','factory_evolution','rollback','generalize_success')),
    causal_level INTEGER NOT NULL CHECK (causal_level BETWEEN 0 AND 6),
    strategy_fingerprint TEXT NOT NULL,
    strategy_json TEXT NOT NULL,
    new_evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','running','succeeded','failed','effective','ineffective','cancelled','superseded')),
    execution_id TEXT REFERENCES executions(id),
    result_json TEXT,
    observed_evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    proposed_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_supervision_actions_incident
    ON supervision_actions(incident_id, proposed_at);
CREATE INDEX IF NOT EXISTS idx_supervision_actions_strategy
    ON supervision_actions(incident_id, strategy_fingerprint, status);

CREATE TABLE IF NOT EXISTS supervision_effectiveness_reviews (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES supervision_incidents(id) ON DELETE CASCADE,
    action_id TEXT NOT NULL REFERENCES supervision_actions(id) ON DELETE CASCADE,
    reviewer_session_id TEXT REFERENCES agent_sessions(id),
    disposition TEXT NOT NULL CHECK (disposition IN ('effective','ineffective','inconclusive','regressed')),
    metrics_json TEXT NOT NULL DEFAULT '{}',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    review_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(action_id, review_fingerprint)
);

CREATE TABLE IF NOT EXISTS retained_adaptive_cases (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    case_type TEXT NOT NULL CHECK (case_type IN ('failure','success','mixed','opportunity')),
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    case_fingerprint TEXT NOT NULL,
    context_json TEXT NOT NULL,
    mechanism_json TEXT NOT NULL,
    trigger_json TEXT NOT NULL,
    outcome_json TEXT NOT NULL,
    response_json TEXT NOT NULL,
    applicability_json TEXT NOT NULL DEFAULT '{}',
    recurrence_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'retained' CHECK (status IN ('candidate','retained','superseded','rejected')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mission_id, case_fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_retained_adaptive_cases_mission_type
    ON retained_adaptive_cases(mission_id, case_type, status);
