-- Immutable libRSI record cache, explicit operational bindings, and cutover receipts.

CREATE TABLE IF NOT EXISTS librsi_records (
    root TEXT PRIMARY KEY,
    record_type TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    canonical_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS librsi_record_bindings (
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    operational_subject_type TEXT NOT NULL,
    operational_subject_id TEXT NOT NULL,
    semantic_role TEXT NOT NULL,
    librsi_root TEXT NOT NULL REFERENCES librsi_records(root),
    currentness_root TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(
        mission_id,
        operational_subject_type,
        operational_subject_id,
        semantic_role,
        librsi_root
    )
);

CREATE INDEX IF NOT EXISTS idx_librsi_bindings_operational
ON librsi_record_bindings(
    mission_id,operational_subject_type,operational_subject_id,semantic_role
);

CREATE TABLE IF NOT EXISTS librsi_cutover_receipts_v2 (
    receipt_root TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    source_execution_id TEXT NOT NULL UNIQUE REFERENCES executions(id) ON DELETE CASCADE,
    adapter_contract TEXT NOT NULL,
    producer_acceptance_revision TEXT NOT NULL,
    source_commit TEXT NOT NULL,
    package_content_root TEXT NOT NULL,
    currentness_root TEXT NOT NULL,
    shadow_projection_root TEXT NOT NULL,
    semantic_result_root TEXT NOT NULL,
    parity_disposition TEXT NOT NULL CHECK(parity_disposition IN ('matched','mismatched')),
    authority_posture TEXT NOT NULL CHECK(authority_posture IN ('shadow','authoritative')),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_librsi_cutover_mission
ON librsi_cutover_receipts_v2(mission_id,authority_posture,created_at);

CREATE UNIQUE INDEX IF NOT EXISTS one_librsi_experiment_work_per_source
ON work_items(mission_id,lane_key)
WHERE lane_key LIKE 'librsi-experiment:%';

CREATE UNIQUE INDEX IF NOT EXISTS one_librsi_followup_work_per_hypothesis
ON work_items(mission_id,lane_key)
WHERE lane_key LIKE 'librsi-followup:%';
