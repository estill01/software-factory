ALTER TABLE agent_sessions ADD COLUMN state_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE workspaces ADD COLUMN mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE workspaces ADD COLUMN work_item_id TEXT REFERENCES work_items(id) ON DELETE SET NULL;
ALTER TABLE workspaces ADD COLUMN created_by_execution_id TEXT REFERENCES executions(id);
ALTER TABLE workspaces ADD COLUMN state_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE work_assignments ADD COLUMN state_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE executions ADD COLUMN workspace_id TEXT REFERENCES workspaces(id);
ALTER TABLE executions ADD COLUMN command_root TEXT;
ALTER TABLE executions ADD COLUMN exit_code INTEGER;
ALTER TABLE executions ADD COLUMN stdout_artifact_id TEXT REFERENCES artifacts(id);
ALTER TABLE executions ADD COLUMN stderr_artifact_id TEXT REFERENCES artifacts(id);
ALTER TABLE executions ADD COLUMN failure_fingerprint TEXT;
ALTER TABLE executions ADD COLUMN expected_effect_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE executions ADD COLUMN observed_effect_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE executions ADD COLUMN state_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE leases ADD COLUMN mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE leases ADD COLUMN repository_id TEXT REFERENCES repositories(id) ON DELETE CASCADE;
ALTER TABLE leases ADD COLUMN resource_kind TEXT NOT NULL DEFAULT 'generic';
ALTER TABLE leases ADD COLUMN resource_path TEXT;
ALTER TABLE qa_requirements ADD COLUMN acceptance_contract_root TEXT;
ALTER TABLE qa_requirements ADD COLUMN state_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE qa_results ADD COLUMN candidate_root TEXT;
ALTER TABLE qa_results ADD COLUMN reviewer_assignment_id TEXT REFERENCES work_assignments(id);
ALTER TABLE artifacts ADD COLUMN mission_id TEXT REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE artifacts ADD COLUMN subject_type TEXT;
ALTER TABLE artifacts ADD COLUMN subject_id TEXT;

CREATE INDEX IF NOT EXISTS idx_agent_sessions_mission_status
ON agent_sessions(mission_id, observed_status, desired_status);

CREATE INDEX IF NOT EXISTS idx_assignments_work_status
ON work_assignments(work_item_id, role, status);

CREATE INDEX IF NOT EXISTS idx_workspaces_mission_status
ON workspaces(mission_id, status, workspace_type);

CREATE INDEX IF NOT EXISTS idx_leases_mission_resource
ON leases(mission_id, repository_id, resource_kind, resource_path, status);

CREATE INDEX IF NOT EXISTS idx_qa_work_phase_status
ON qa_requirements(work_item_id, phase, status);
