-- Reconcile runtime-referenced operational tables into the one active schema.
-- The pre-existing signal_evaluations table remains the immutable legacy lane;
-- current learned-signal evaluation uses the explicitly versioned table below.

CREATE TABLE IF NOT EXISTS acceptance_runs (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    source_revision TEXT NOT NULL,
    source_tree TEXT,
    matrix_sha256 TEXT NOT NULL,
    matrix_json TEXT NOT NULL,
    test_root TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('queued','running','passed','failed')),
    evidence_root TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_acceptance_runs_revision
ON acceptance_runs(source_revision,status,created_at);

CREATE TABLE IF NOT EXISTS acceptance_case_results (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES acceptance_runs(id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    test_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','passed','failed','error')),
    exit_code INTEGER,
    stdout_sha256 TEXT,
    stderr_sha256 TEXT,
    duration_ms INTEGER,
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(run_id,domain,test_id)
);

CREATE TABLE IF NOT EXISTS observed_stream_events (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    classification TEXT NOT NULL CHECK(classification IN (
        'neutral','progress','failure','success','mixed','opportunity'
    )),
    attributes_json TEXT NOT NULL DEFAULT '{}',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    occurred_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    historical_only INTEGER NOT NULL DEFAULT 0 CHECK(historical_only IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_observed_stream_events_mission
ON observed_stream_events(mission_id,occurred_at,id);

CREATE TABLE IF NOT EXISTS learned_signal_candidates (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    signal_kind TEXT NOT NULL CHECK(signal_kind IN ('failure','success','mixed','opportunity')),
    name TEXT NOT NULL,
    candidate_fingerprint TEXT NOT NULL,
    detector_spec_json TEXT NOT NULL,
    response_spec_json TEXT NOT NULL,
    discovery_evidence_json TEXT NOT NULL,
    counterexamples_json TEXT NOT NULL DEFAULT '[]',
    replay_status TEXT NOT NULL DEFAULT 'pending' CHECK(replay_status IN (
        'pending','passed','failed','inconclusive'
    )),
    shadow_status TEXT NOT NULL DEFAULT 'pending' CHECK(shadow_status IN (
        'pending','passed','failed','inconclusive'
    )),
    canary_status TEXT NOT NULL DEFAULT 'pending' CHECK(canary_status IN (
        'pending','passed','failed','inconclusive'
    )),
    qa_status TEXT NOT NULL DEFAULT 'pending' CHECK(qa_status IN (
        'pending','passed','failed','inconclusive'
    )),
    status TEXT NOT NULL CHECK(status IN (
        'candidate','evaluating','promoted','rejected','superseded'
    )),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mission_id,candidate_fingerprint)
);

CREATE TABLE IF NOT EXISTS signal_evaluations_v2 (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES learned_signal_candidates(id) ON DELETE CASCADE,
    phase TEXT NOT NULL CHECK(phase IN ('historical_replay','shadow','canary','qa')),
    disposition TEXT NOT NULL CHECK(disposition IN ('passed','failed','inconclusive')),
    metrics_json TEXT NOT NULL DEFAULT '{}',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    evaluator_session_id TEXT REFERENCES agent_sessions(id),
    created_at TEXT NOT NULL,
    UNIQUE(candidate_id,phase)
);

CREATE TABLE IF NOT EXISTS active_signal_bundles (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL REFERENCES learned_signal_candidates(id),
    signal_kind TEXT NOT NULL,
    detector_spec_json TEXT NOT NULL,
    response_spec_json TEXT NOT NULL,
    bundle_root TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'active','narrowed','revising','rolled_back','retired'
    )),
    activated_by_session_id TEXT REFERENCES agent_sessions(id),
    activated_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mission_id,bundle_root,version)
);

CREATE TABLE IF NOT EXISTS signal_occurrences (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    bundle_id TEXT NOT NULL REFERENCES active_signal_bundles(id) ON DELETE CASCADE,
    event_id TEXT NOT NULL REFERENCES observed_stream_events(id) ON DELETE CASCADE,
    match_json TEXT NOT NULL,
    routed_action_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('routed','succeeded','failed')),
    created_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE(bundle_id,event_id)
);

CREATE TABLE IF NOT EXISTS signal_effectiveness_reviews (
    id TEXT PRIMARY KEY,
    occurrence_id TEXT NOT NULL REFERENCES signal_occurrences(id) ON DELETE CASCADE,
    bundle_id TEXT NOT NULL REFERENCES active_signal_bundles(id) ON DELETE CASCADE,
    disposition TEXT NOT NULL CHECK(disposition IN (
        'effective','ineffective','false_positive','false_negative','harmful','inconclusive'
    )),
    recurrence_detected INTEGER NOT NULL CHECK(recurrence_detected IN (0,1)),
    metrics_json TEXT NOT NULL DEFAULT '{}',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reflections_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    reflection_type TEXT NOT NULL CHECK(reflection_type IN (
        'live','checkpoint','terminal','cross_run','meta'
    )),
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    prompt_root TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    observations_json TEXT NOT NULL DEFAULT '{}',
    conclusions_json TEXT NOT NULL DEFAULT '{}',
    proposed_actions_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    status TEXT NOT NULL CHECK(status IN ('advisory','applied','rejected','superseded')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hypotheses_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    statement TEXT NOT NULL,
    causal_model_json TEXT NOT NULL,
    prediction_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'proposed','testing','supported','rejected','weakened'
    )),
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    created_from_reflection_id TEXT REFERENCES reflections_v2(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hypothesis_evidence_v2 (
    id TEXT PRIMARY KEY,
    hypothesis_id TEXT NOT NULL REFERENCES hypotheses_v2(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL CHECK(evidence_type IN (
        'support','counterexample','boundary','confounder','null'
    )),
    evidence_id TEXT NOT NULL,
    weight REAL NOT NULL CHECK(weight >= 0.0 AND weight <= 1.0),
    rationale_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiments_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    hypothesis_id TEXT REFERENCES hypotheses_v2(id),
    experiment_type TEXT NOT NULL CHECK(experiment_type IN (
        'command','historical_replay','shadow','canary','simulation','comparison'
    )),
    design_json TEXT NOT NULL,
    success_criteria_json TEXT NOT NULL,
    safety_constraints_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK(status IN ('designed','running','succeeded','failed','invalid')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiment_runs_v2 (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments_v2(id) ON DELETE CASCADE,
    exact_input_root TEXT NOT NULL,
    command_json TEXT NOT NULL,
    cwd TEXT NOT NULL,
    exit_code INTEGER,
    stdout_text TEXT,
    stderr_text TEXT,
    measurement_json TEXT NOT NULL DEFAULT '{}',
    evidence_root TEXT,
    disposition TEXT NOT NULL CHECK(disposition IN ('running','passed','failed','invalid')),
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_learned_signal_candidates_mission
ON learned_signal_candidates(mission_id,status,created_at);
CREATE INDEX IF NOT EXISTS idx_signal_evaluations_v2_candidate
ON signal_evaluations_v2(candidate_id,phase,disposition);
CREATE INDEX IF NOT EXISTS idx_active_signal_bundles_mission
ON active_signal_bundles(mission_id,status,activated_at);
CREATE INDEX IF NOT EXISTS idx_signal_occurrences_mission
ON signal_occurrences(mission_id,status,created_at);
CREATE INDEX IF NOT EXISTS idx_reflections_v2_mission
ON reflections_v2(mission_id,created_at);
CREATE INDEX IF NOT EXISTS idx_hypotheses_v2_mission
ON hypotheses_v2(mission_id,status,created_at);
CREATE INDEX IF NOT EXISTS idx_experiments_v2_mission
ON experiments_v2(mission_id,status,created_at);
