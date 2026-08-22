CREATE TABLE IF NOT EXISTS supervision_assignments (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    supervisor_session_id TEXT REFERENCES agent_sessions(id),
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    trigger_mode TEXT NOT NULL,
    trigger_spec_json TEXT NOT NULL DEFAULT '{}',
    policy_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK(status IN ('active','paused','completed','cancelled')),
    last_check_execution_id TEXT REFERENCES executions(id),
    last_checked_at TEXT,
    next_due_at TEXT,
    replacement_history_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NULL
);

CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('open','contained','correcting','verifying','resolved','superseded')),
    layer TEXT NOT NULL,
    mechanism TEXT NOT NULL,
    trigger_json TEXT NOT NULL,
    effect_json TEXT NOT NULL,
    detection_json TEXT NOT NULL,
    containment_json TEXT NOT NULL DEFAULT '{}',
    correction_json TEXT NOT NULL DEFAULT '{}',
    recurrence_invariant_json TEXT NOT NULL DEFAULT '{}',
    human_scheduling_leak INTEGER NOT NULL DEFAULT 0,
    owner_assignment_id TEXT REFERENCES work_assignments(id),
    effectiveness TEXT,
    reusable_disposition TEXT,
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hypotheses (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    obligation_id TEXT REFERENCES obligations(id),
    origin_execution_id TEXT REFERENCES executions(id),
    parent_hypothesis_id TEXT REFERENCES hypotheses(id),
    hypothesis_type TEXT NOT NULL,
    statement TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'proposed','challenged','selected_for_test','testing','supported',
        'refuted','inconclusive','superseded','retired'
    )),
    scope_json TEXT NOT NULL DEFAULT '{}',
    expected_evidence_json TEXT NOT NULL DEFAULT '{}',
    supporting_evidence_json TEXT NOT NULL DEFAULT '[]',
    contrary_evidence_json TEXT NOT NULL DEFAULT '[]',
    uncertainty_json TEXT NOT NULL DEFAULT '{}',
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS classifiers (
    id TEXT PRIMARY KEY,
    classifier_key TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('candidate','shadow','canary','active','retired','rolled_back')),
    implementation_type TEXT NOT NULL,
    implementation_json TEXT NOT NULL,
    output_schema_json TEXT NOT NULL DEFAULT '{}',
    labels_json TEXT NOT NULL,
    applicability_json TEXT NOT NULL DEFAULT '{}',
    rollback_classifier_id TEXT REFERENCES classifiers(id),
    created_at TEXT NOT NULL,
    retired_at TEXT,
    UNIQUE(classifier_key, version)
);

CREATE TABLE IF NOT EXISTS classifications (
    id TEXT PRIMARY KEY,
    classifier_id TEXT NOT NULL REFERENCES classifiers(id),
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    stream_key TEXT NOT NULL,
    window_start_sequence INTEGER,
    window_end_sequence INTEGER,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    label TEXT NOT NULL,
    severity TEXT,
    confidence_band TEXT,
    evidence_event_ids_json TEXT NOT NULL,
    result_json TEXT NOT NULL DEFAULT '{}',
    origin TEXT NOT NULL DEFAULT 'live',
    dedup_key TEXT NOT NULL UNIQUE,
    supersedes_id TEXT REFERENCES classifications(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    rule_key TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('candidate','shadow','canary','active','retired','rolled_back')),
    classifier_id TEXT REFERENCES classifiers(id),
    trigger_spec_json TEXT NOT NULL,
    state_preconditions_json TEXT NOT NULL DEFAULT '{}',
    command_spec_json TEXT NOT NULL,
    authority_limits_json TEXT NOT NULL DEFAULT '{}',
    rollback_rule_id TEXT REFERENCES rules(id),
    created_at TEXT NOT NULL,
    retired_at TEXT,
    UNIQUE(rule_key, version)
);

CREATE TABLE IF NOT EXISTS signal_candidates (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    signal_kind TEXT NOT NULL CHECK(signal_kind IN ('failure','success','mixed','opportunity')),
    status TEXT NOT NULL CHECK(status IN (
        'observed','hypothesized','replay_evaluated','shadow','canary',
        'independently_reviewed','active','effective','mixed','ineffective',
        'regressed','narrowed','revised','rolled_back','retired'
    )),
    source_window_json TEXT NOT NULL,
    definition_json TEXT NOT NULL,
    applicability_json TEXT NOT NULL DEFAULT '{}',
    counterexamples_json TEXT NOT NULL DEFAULT '[]',
    hypothesis_id TEXT REFERENCES hypotheses(id),
    classifier_id TEXT REFERENCES classifiers(id),
    rule_id TEXT REFERENCES rules(id),
    evaluation_json TEXT NOT NULL DEFAULT '{}',
    effectiveness_json TEXT NOT NULL DEFAULT '{}',
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS policies (
    id TEXT PRIMARY KEY,
    policy_key TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('candidate','shadow','canary','active','retired','rolled_back')),
    policy_json TEXT NOT NULL,
    incumbent_id TEXT REFERENCES policies(id),
    evaluation_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    retired_at TEXT,
    UNIQUE(policy_key, version)
);

CREATE TABLE IF NOT EXISTS selections (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    selection_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('proposed','under_review','accepted','revised','rejected','deferred')),
    generator_session_id TEXT REFERENCES agent_sessions(id),
    selector_session_id TEXT REFERENCES agent_sessions(id),
    reviewer_session_id TEXT REFERENCES agent_sessions(id),
    inventory_root TEXT NOT NULL,
    candidate_ids_json TEXT NOT NULL,
    selected_ids_json TEXT NOT NULL,
    rejected_ids_json TEXT NOT NULL DEFAULT '[]',
    forecasts_json TEXT NOT NULL DEFAULT '{}',
    uncertainty_json TEXT NOT NULL DEFAULT '{}',
    policy_id TEXT REFERENCES policies(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS selection_outcomes (
    id TEXT PRIMARY KEY,
    selection_id TEXT NOT NULL REFERENCES selections(id) ON DELETE CASCADE,
    evaluator_session_id TEXT REFERENCES agent_sessions(id),
    outcome_json TEXT NOT NULL,
    counterfactual_json TEXT NOT NULL DEFAULT '{}',
    disposition TEXT NOT NULL,
    observed_at TEXT NOT NULL
);
