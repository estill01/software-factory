-- Revision-bound staged acceptance and actual-outcome reconciliation.

CREATE TABLE IF NOT EXISTS acceptance_stage_records_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    work_item_id TEXT REFERENCES work_items(id) ON DELETE CASCADE,
    scope_key TEXT NOT NULL,
    stage TEXT NOT NULL CHECK(stage IN ('candidate','integrated','installed','terminal')),
    target_revision TEXT NOT NULL,
    currentness_root TEXT NOT NULL,
    expected_outcome_json TEXT NOT NULL,
    outcome_contract_root TEXT NOT NULL,
    remaining_scope_json TEXT NOT NULL DEFAULT '[]',
    contract_id TEXT NOT NULL UNIQUE REFERENCES acceptance_contracts_v2(id),
    decision_id TEXT UNIQUE REFERENCES acceptance_decisions_v2(id),
    prior_stage_id TEXT REFERENCES acceptance_stage_records_v2(id),
    implementer_session_id TEXT NOT NULL REFERENCES agent_sessions(id),
    status TEXT NOT NULL DEFAULT 'prepared' CHECK(status IN (
        'prepared','accepted','reopened','stale','superseded'
    )),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(scope_key,stage,target_revision,currentness_root)
);

CREATE INDEX IF NOT EXISTS idx_acceptance_stage_mission
ON acceptance_stage_records_v2(mission_id,stage,status,created_at);

CREATE TABLE IF NOT EXISTS outcome_reconciliations_v2 (
    id TEXT PRIMARY KEY,
    stage_record_id TEXT NOT NULL REFERENCES acceptance_stage_records_v2(id) ON DELETE CASCADE,
    reviewer_session_id TEXT NOT NULL REFERENCES agent_sessions(id),
    exact_revision TEXT NOT NULL,
    currentness_root TEXT NOT NULL,
    expected_outcome_json TEXT NOT NULL,
    observed_outcome_json TEXT NOT NULL,
    mismatches_json TEXT NOT NULL DEFAULT '[]',
    evidence_ids_json TEXT NOT NULL,
    disposition TEXT NOT NULL CHECK(disposition IN ('aligned','disagreed','inconclusive')),
    outcome_root TEXT NOT NULL,
    narrow_owner_type TEXT,
    narrow_owner_id TEXT,
    obligation_id TEXT REFERENCES obligations(id),
    incident_id TEXT REFERENCES incidents(id),
    created_at TEXT NOT NULL,
    UNIQUE(stage_record_id,outcome_root)
);

CREATE INDEX IF NOT EXISTS idx_outcome_reconciliation_stage
ON outcome_reconciliations_v2(stage_record_id,created_at,disposition);
