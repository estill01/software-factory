-- Self-directed problem solving, alternative strategies, and next-action selection.

CREATE TABLE IF NOT EXISTS problem_solving_cycles_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    trigger_type TEXT NOT NULL,
    trigger_id TEXT NOT NULL,
    objective_json TEXT NOT NULL,
    governing_range_root TEXT NOT NULL,
    state_root TEXT NOT NULL,
    causal_level INTEGER NOT NULL DEFAULT 0 CHECK (causal_level BETWEEN 0 AND 6),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','experimenting','executing','verifying','resolved','superseded','failed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(mission_id,trigger_type,trigger_id,state_root)
);

CREATE TABLE IF NOT EXISTS strategy_candidates_v2 (
    id TEXT PRIMARY KEY,
    cycle_id TEXT NOT NULL REFERENCES problem_solving_cycles_v2(id) ON DELETE CASCADE,
    strategy_type TEXT NOT NULL CHECK (strategy_type IN ('local_repair','alternate_implementation','candidate_comparison','architecture_change','program_revision','selection_reconsideration','factory_evolution','experiment','success_generalization')),
    strategy_fingerprint TEXT NOT NULL,
    rationale_json TEXT NOT NULL,
    expected_effect_json TEXT NOT NULL,
    writable_scope_json TEXT NOT NULL DEFAULT '[]',
    prerequisites_json TEXT NOT NULL DEFAULT '[]',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    proposer_session_id TEXT REFERENCES agent_sessions(id),
    selected_by_session_id TEXT REFERENCES agent_sessions(id),
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','selected','running','succeeded','failed','ineffective','rejected','superseded')),
    result_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(cycle_id,strategy_fingerprint)
);

CREATE TABLE IF NOT EXISTS problem_experiment_designs_v2 (
    id TEXT PRIMARY KEY,
    cycle_id TEXT NOT NULL REFERENCES problem_solving_cycles_v2(id) ON DELETE CASCADE,
    strategy_id TEXT REFERENCES strategy_candidates_v2(id) ON DELETE SET NULL,
    hypothesis_id TEXT REFERENCES hypotheses_v2(id) ON DELETE SET NULL,
    design_root TEXT NOT NULL,
    question TEXT NOT NULL,
    experiment_spec_json TEXT NOT NULL,
    expected_discrimination_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'designed' CHECK (status IN ('designed','running','succeeded','failed','invalid','cancelled')),
    experiment_id TEXT REFERENCES experiments_v2(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(cycle_id,design_root)
);

CREATE TABLE IF NOT EXISTS next_action_decisions_v2 (
    id TEXT PRIMARY KEY,
    cycle_id TEXT NOT NULL REFERENCES problem_solving_cycles_v2(id) ON DELETE CASCADE,
    decision_root TEXT NOT NULL,
    selected_strategy_ids_json TEXT NOT NULL,
    selected_by_session_id TEXT REFERENCES agent_sessions(id),
    rationale_json TEXT NOT NULL,
    authority_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'selected' CHECK (status IN ('selected','dispatched','completed','revised','cancelled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(cycle_id,decision_root)
);
