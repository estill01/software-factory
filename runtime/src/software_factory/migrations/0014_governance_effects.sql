-- Independent role grants, fail-closed acceptance, and external-effect reconciliation.

CREATE TABLE IF NOT EXISTS role_grants_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    grantee_session_id TEXT NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_revision TEXT,
    policy_root TEXT NOT NULL,
    currentness_root TEXT NOT NULL,
    scope_json TEXT NOT NULL DEFAULT '{}',
    issued_by_session_id TEXT REFERENCES agent_sessions(id),
    parent_grant_id TEXT REFERENCES role_grants_v2(id),
    max_uses INTEGER NOT NULL DEFAULT 1 CHECK (max_uses > 0),
    use_count INTEGER NOT NULL DEFAULT 0 CHECK (use_count >= 0),
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','consumed','expired','revoked','superseded')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(grantee_session_id,role,target_type,target_id,target_revision,policy_root,currentness_root)
);
CREATE INDEX IF NOT EXISTS idx_role_grants_target
    ON role_grants_v2(target_type,target_id,target_revision,role,status);

CREATE TABLE IF NOT EXISTS acceptance_contracts_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_revision TEXT NOT NULL,
    acceptance_spec_root TEXT NOT NULL,
    required_probes_json TEXT NOT NULL,
    protected_capabilities_json TEXT NOT NULL DEFAULT '[]',
    minimum_independent_reviews INTEGER NOT NULL DEFAULT 1 CHECK (minimum_independent_reviews > 0),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','satisfied','stale','superseded','cancelled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(target_type,target_id,target_revision,acceptance_spec_root)
);

CREATE TABLE IF NOT EXISTS acceptance_probe_results_v2 (
    id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL REFERENCES acceptance_contracts_v2(id) ON DELETE CASCADE,
    probe_key TEXT NOT NULL,
    probe_type TEXT NOT NULL,
    exact_revision TEXT NOT NULL,
    command_json TEXT,
    observed_result_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    disposition TEXT NOT NULL CHECK (disposition IN ('passed','failed','inconclusive','invalid')),
    observer_session_id TEXT REFERENCES agent_sessions(id),
    created_at TEXT NOT NULL,
    UNIQUE(contract_id,probe_key,exact_revision)
);

CREATE TABLE IF NOT EXISTS independent_review_executions_v2 (
    id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL REFERENCES acceptance_contracts_v2(id) ON DELETE CASCADE,
    grant_id TEXT NOT NULL REFERENCES role_grants_v2(id),
    reviewer_session_id TEXT NOT NULL REFERENCES agent_sessions(id),
    implementer_session_id TEXT REFERENCES agent_sessions(id),
    exact_revision TEXT NOT NULL,
    review_contract_root TEXT NOT NULL,
    provider_session_id TEXT NOT NULL,
    transcript_artifact_id TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    disposition TEXT NOT NULL CHECK (disposition IN ('accepted','rejected','revise','inconclusive')),
    findings_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed','invalidated','superseded')),
    created_at TEXT NOT NULL,
    UNIQUE(contract_id,grant_id,exact_revision,review_contract_root)
);

CREATE TABLE IF NOT EXISTS acceptance_decisions_v2 (
    id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL REFERENCES acceptance_contracts_v2(id) ON DELETE CASCADE,
    exact_revision TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('accepted','rejected','stale')),
    probe_result_ids_json TEXT NOT NULL,
    review_execution_ids_json TEXT NOT NULL,
    evidence_root TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    UNIQUE(contract_id,exact_revision,evidence_root)
);

CREATE TABLE IF NOT EXISTS external_effect_intents_v2 (
    id TEXT PRIMARY KEY,
    mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE,
    effect_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    command_root TEXT NOT NULL,
    request_json TEXT NOT NULL,
    probe_spec_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'claimed' CHECK (status IN ('claimed','started','observed','succeeded','failed','ambiguous','cancelled')),
    lease_owner TEXT,
    lease_expires_at TEXT,
    provider_reference TEXT,
    observed_result_json TEXT,
    error_json TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    observed_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_external_effect_intents_reconcile
    ON external_effect_intents_v2(status,lease_expires_at);

CREATE TABLE IF NOT EXISTS notification_report_links_v2 (
    notification_id TEXT NOT NULL REFERENCES notifications_v2(id) ON DELETE CASCADE,
    report_id TEXT NOT NULL REFERENCES reports_v2(id) ON DELETE CASCADE,
    PRIMARY KEY(notification_id,report_id)
);
