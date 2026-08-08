# Terminal capability reconciliation

Use this caller-owned JSON only for the independent terminal outcome review.
The helper validates the object, computes a canonical normalized SHA-256, and
stores only that root plus the reviewer, implementation owner, revision,
posture, and gap count. It does not copy this source object into the canonical
event ledger.

The object has these exact top-level keys:

```json
{
  "schema_version": 1,
  "kind": "software-factory-terminal-capability-reconciliation",
  "target_thread_id": "target-thread-id",
  "mission_root": "64-lowercase-hex",
  "state_fingerprint": "current-state-fingerprint",
  "current_revision": "40-or-64-lowercase-hex",
  "implementation_owner_id": "target-or-implementer-id",
  "reviewer_id": "bound-base-or-max-reviewer-thread-id",
  "requested_capability": {
    "statement": "The direct requested capability.",
    "evidence_ids": ["authority-0001"]
  },
  "protected_capabilities": [{
    "statement": "Behavior that must remain available.",
    "evidence_ids": ["repository-0001"]
  }],
  "selected_architecture_level": {
    "level": "local, bounded-general, or existing architectural owner",
    "owner_ref": "exact owning skill or repository component",
    "evidence_ids": ["repository-0001"]
  },
  "accepted_tradeoffs": [{
    "statement": "A supported tradeoff, including an explicit none posture.",
    "evidence_ids": ["authority-0001", "repository-0001"]
  }],
  "current_behavior": {
    "statement": "Behavior observed at the frozen current revision.",
    "evidence_ids": ["outcome-0001"]
  },
  "operator_visible_effects": [{
    "statement": "A current observable effect, not a process proxy.",
    "evidence_ids": ["outcome-0001"]
  }],
  "supported_gaps": [],
  "completion_posture": "verified",
  "evidence": [
    {"evidence_id": "authority-0001", "evidence_class": "direct-authority", "source_root": "64-lowercase-hex"},
    {"evidence_id": "repository-0001", "evidence_class": "current-repository", "source_root": "64-lowercase-hex"},
    {"evidence_id": "outcome-0001", "evidence_class": "observed-outcome", "source_root": "64-lowercase-hex"}
  ]
}
```

Every claim object has exactly `statement` and `evidence_ids`. Every evidence
object has exactly `evidence_id`, `evidence_class`, and `source_root`. Accepted
evidence classes are `direct-authority`, `current-repository`,
`observed-outcome`, `validation`, and `independent-review`. Requested capability
requires direct-authority evidence; architecture requires current-repository
evidence; current behavior and every operator-visible effect require observed-
outcome evidence. Validation or populated artifacts alone cannot satisfy those
claims.

If a supported gap exists, use this exact gap shape:

```json
{"gap_id": "gap-0001", "statement": "Current observed gap.", "owner_class": "supervision", "owner_ref": "supervise-tracker-runs", "evidence_ids": ["outcome-0001"]}
```

Accepted `owner_class` values are `authoring`, `implementation`, `supervision`,
and `target-repository`. Every gap requires observed-outcome evidence. Any gap
requires `completion_posture: "reopen-narrow-owner"` and prevents a verified
completion record. With no gaps, posture must be `verified`; the overall
completion record may still be `failed` when another outcome root fails.

Invoke the helper with both the current revision and the JSON path:

```bash
python3 <LOG_HELPER> completion-record --target-thread <TARGET> \
  --state-fingerprint <HASH> --current-revision <COMMIT_OR_ROOT> \
  --mission-root <MISSION_SHA256> --status <verified|failed> \
  --model gpt-5.6-sol --reasoning xhigh \
  --outcome-manifest-sha256 <SHA256> \
  --artifact-currentness-sha256 <SHA256> \
  --effect-reconciliation-sha256 <SHA256> \
  --open-item-compatibility-sha256 <SHA256> \
  --independent-challenge-sha256 <SHA256> \
  --capability-reconciliation-json <PATH> \
  --evidence <EXACT_SOURCE_ID> --summary "Outcome independently checked."
```
