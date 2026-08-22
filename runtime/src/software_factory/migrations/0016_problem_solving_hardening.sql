-- Attempt history and semantic identity for self-directed problem solving.

ALTER TABLE strategy_candidates_v2
    ADD COLUMN strategy_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE strategy_candidates_v2
    ADD COLUMN semantic_fingerprint TEXT;
ALTER TABLE strategy_candidates_v2
    ADD COLUMN priority INTEGER NOT NULL DEFAULT 0;
ALTER TABLE strategy_candidates_v2
    ADD COLUMN expected_value REAL NOT NULL DEFAULT 0.0;
ALTER TABLE strategy_candidates_v2
    ADD COLUMN estimated_cost REAL NOT NULL DEFAULT 0.0;
ALTER TABLE strategy_candidates_v2
    ADD COLUMN estimated_risk REAL NOT NULL DEFAULT 0.0;

CREATE INDEX IF NOT EXISTS idx_strategy_candidates_cycle_semantic
    ON strategy_candidates_v2(cycle_id,semantic_fingerprint,status);
CREATE INDEX IF NOT EXISTS idx_strategy_candidates_cycle_priority
    ON strategy_candidates_v2(cycle_id,status,priority DESC,expected_value DESC);

CREATE TABLE IF NOT EXISTS strategy_attempts_v2 (
    id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL REFERENCES strategy_candidates_v2(id) ON DELETE CASCADE,
    cycle_id TEXT NOT NULL REFERENCES problem_solving_cycles_v2(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    agent_session_id TEXT REFERENCES agent_sessions(id),
    execution_id TEXT REFERENCES executions(id),
    basis_evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    exact_input_root TEXT NOT NULL,
    result_json TEXT,
    observed_evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    disposition TEXT NOT NULL DEFAULT 'running' CHECK (disposition IN ('running','succeeded','failed','ineffective','cancelled','invalid')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE(strategy_id,attempt_number),
    UNIQUE(cycle_id,exact_input_root)
);

CREATE TABLE IF NOT EXISTS problem_cycle_verifications_v2 (
    id TEXT PRIMARY KEY,
    cycle_id TEXT NOT NULL REFERENCES problem_solving_cycles_v2(id) ON DELETE CASCADE,
    disposition TEXT NOT NULL CHECK (disposition IN ('effective','ineffective','inconclusive','regressed')),
    metrics_json TEXT NOT NULL DEFAULT '{}',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    verifier_session_id TEXT REFERENCES agent_sessions(id),
    verification_root TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(cycle_id,verification_root)
);
