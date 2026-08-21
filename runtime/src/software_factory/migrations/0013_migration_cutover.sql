-- Legacy inventory, historical migration, parity, one-writer cutover, and rollback.

CREATE TABLE IF NOT EXISTS migration_runs_v2 (
    id TEXT PRIMARY KEY,
    source_root TEXT NOT NULL,
    source_inventory_root TEXT NOT NULL,
    backup_path TEXT,
    backup_root TEXT,
    status TEXT NOT NULL DEFAULT 'inventoried' CHECK (status IN ('inventoried','backed_up','importing','imported','parity','cutting_over','cutover','rolling_back','rolled_back','failed')),
    current_step TEXT,
    error_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE(source_root,source_inventory_root)
);

CREATE TABLE IF NOT EXISTS migration_items_v2 (
    id TEXT PRIMARY KEY,
    migration_id TEXT NOT NULL REFERENCES migration_runs_v2(id) ON DELETE CASCADE,
    relative_path TEXT NOT NULL,
    item_kind TEXT NOT NULL CHECK (item_kind IN ('event','tracker','test','fixture','report','failure','success','state','skill','dashboard','release','other')),
    sha256 TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    historical_only INTEGER NOT NULL DEFAULT 1 CHECK (historical_only IN (0,1)),
    import_status TEXT NOT NULL DEFAULT 'pending' CHECK (import_status IN ('pending','imported','mapped','rejected','failed','preserved_only')),
    native_reference_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(migration_id,relative_path)
);

CREATE TABLE IF NOT EXISTS parity_cases_v2 (
    id TEXT PRIMARY KEY,
    migration_id TEXT NOT NULL REFERENCES migration_runs_v2(id) ON DELETE CASCADE,
    legacy_path TEXT NOT NULL,
    legacy_case_key TEXT NOT NULL,
    capability_domain TEXT NOT NULL,
    native_test_ids_json TEXT NOT NULL DEFAULT '[]',
    disposition TEXT NOT NULL DEFAULT 'pending' CHECK (disposition IN ('pending','equivalent','stronger_replacement','deferred','rejected','unmapped')),
    rationale_json TEXT NOT NULL DEFAULT '{}',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(migration_id,legacy_path,legacy_case_key)
);

CREATE TABLE IF NOT EXISTS cutover_effects_v2 (
    id TEXT PRIMARY KEY,
    migration_id TEXT NOT NULL REFERENCES migration_runs_v2(id) ON DELETE CASCADE,
    repository_root TEXT NOT NULL,
    native_runtime_root TEXT NOT NULL,
    legacy_archive_root TEXT NOT NULL,
    move_manifest_json TEXT NOT NULL,
    active_writer_probe_json TEXT NOT NULL DEFAULT '{}',
    one_writer_verified INTEGER NOT NULL DEFAULT 0 CHECK (one_writer_verified IN (0,1)),
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','running','applied','verified','failed','rolling_back','rolled_back')),
    started_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE(migration_id,repository_root)
);

CREATE TABLE IF NOT EXISTS cutover_path_effects_v2 (
    id TEXT PRIMARY KEY,
    cutover_id TEXT NOT NULL REFERENCES cutover_effects_v2(id) ON DELETE CASCADE,
    source_path TEXT NOT NULL,
    destination_path TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    effect_status TEXT NOT NULL DEFAULT 'planned' CHECK (effect_status IN ('planned','moved','verified','restored','failed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(cutover_id,source_path)
);
