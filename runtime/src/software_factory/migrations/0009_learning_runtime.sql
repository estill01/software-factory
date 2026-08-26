ALTER TABLE strategy_outcomes ADD COLUMN origin TEXT NOT NULL DEFAULT 'live';
ALTER TABLE strategy_outcomes ADD COLUMN source_sequence INTEGER;

ALTER TABLE classifiers ADD COLUMN definition_root TEXT;
ALTER TABLE rules ADD COLUMN bundle_key TEXT;
ALTER TABLE signal_candidates ADD COLUMN definition_root TEXT;
ALTER TABLE signal_candidates ADD COLUMN detector_route_root TEXT;
ALTER TABLE signal_candidates ADD COLUMN activated_at TEXT;
ALTER TABLE signal_candidates ADD COLUMN live_occurrence_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE signal_candidates ADD COLUMN last_live_at TEXT;
ALTER TABLE hypotheses ADD COLUMN current_evidence_root TEXT;
ALTER TABLE hypotheses ADD COLUMN last_tested_at TEXT;
ALTER TABLE experiments ADD COLUMN environment_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE experiments ADD COLUMN reviewer_session_id TEXT REFERENCES agent_sessions(id);
ALTER TABLE experiments ADD COLUMN conclusion_evidence_json TEXT NOT NULL DEFAULT '[]';

CREATE TABLE signal_evaluations (
    id TEXT PRIMARY KEY,
    signal_candidate_id TEXT NOT NULL REFERENCES signal_candidates(id) ON DELETE CASCADE,
    stage TEXT NOT NULL CHECK(stage IN ('replay','shadow','canary','independent_review','live')),
    status TEXT NOT NULL CHECK(status IN ('passed','failed','inconclusive')),
    evaluator_session_id TEXT REFERENCES agent_sessions(id),
    execution_id TEXT REFERENCES executions(id),
    source_ids_json TEXT NOT NULL DEFAULT '[]',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    UNIQUE(signal_candidate_id,stage)
);

CREATE TABLE signal_route_invocations (
    id TEXT PRIMARY KEY,
    signal_candidate_id TEXT NOT NULL REFERENCES signal_candidates(id) ON DELETE CASCADE,
    classification_id TEXT NOT NULL UNIQUE REFERENCES classifications(id) ON DELETE CASCADE,
    rule_id TEXT NOT NULL REFERENCES rules(id),
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    source_outcome_id TEXT REFERENCES strategy_outcomes(id),
    status TEXT NOT NULL CHECK(status IN ('planned','applied','failed','rolled_back')),
    effect_type TEXT NOT NULL,
    effect_id TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE route_effectiveness (
    id TEXT PRIMARY KEY,
    invocation_id TEXT NOT NULL REFERENCES signal_route_invocations(id) ON DELETE CASCADE,
    evaluator_session_id TEXT REFERENCES agent_sessions(id),
    outcome TEXT NOT NULL CHECK(outcome IN (
        'effective','partially_effective','ineffective','counterproductive',
        'inconclusive','not_yet_observable'
    )),
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    observations_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX one_signal_candidate_definition
ON signal_candidates(mission_id,definition_root)
WHERE definition_root IS NOT NULL
  AND status NOT IN ('revised','rolled_back','retired');

CREATE INDEX idx_signal_evaluations_candidate_stage
ON signal_evaluations(signal_candidate_id,stage,status);

CREATE INDEX idx_signal_route_mission
ON signal_route_invocations(mission_id,status,created_at);

CREATE INDEX idx_strategy_outcome_discovery
ON strategy_outcomes(mission_id,origin,outcome,strategy_key,failure_fingerprint,created_at);
