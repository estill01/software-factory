# Program evidence packet

The Block 1 packet is a deterministic, content-minimized checkpoint projection.
It provides current evidence to later reflection; it performs no semantic
judgment and grants no downstream authority.

## Exact input

The input has exactly the fields named by `checkpoint_input_schema` in
`fixtures/product_program_contract_v1.json`:

- `schema_version` is integer `1` and `profile` is
  `target-product-program`.
- `mission` binds `mission_root`, `source_record`, and `source_sha256`.
- `repository` binds the absolute non-symlink Git root, exact `revision`, and
  exact tree.
- `tracker` binds its absolute path, byte SHA-256, and structural root.
- `range` binds requested/accepted Blocks and one exact canonical range-head
  source descriptor.
- `current_outcome` binds status, root, and exact evidence IDs.
- `protected_capabilities` binds IDs, source roots, and current result.
- `product_sources`, `reports`, and `resource_sources` are bounded source
  descriptors. Decision and incident identities are derived from matching
  records in the bounded supervision event source.
- `supervision` binds the exact target ID plus policy and event source
  descriptors.
- `prior_checkpoint_identity` is either `null` or the exact prior semantic and
  currentness roots.

A source descriptor has exactly `source_id`, `path`, `owner_root`, `sha256`, and
`evidence_class`. Paths and roots are literal absolute paths; `$HOME`, `~`, `/`
as an owner root, symlinks, escapes, nonregular files, changing identities, and
files above the byte ceiling reject. Resource sources use only `observed`,
`provider-reported`, `estimated`, `inferred`, or `unavailable`.

The range-head file is canonical JSON with exactly `target_thread_id`,
`requested_blocks`, and `range_head`. Its target and requested set must match the
checkpoint. Caller-supplied authority fields are extra keys and reject.

## Derived identities

`material_change_fingerprint` hashes mission, profile, repository revision/tree,
content identities for product sources, tracker structural state, the requested/
accepted/remaining frontier, outcome, protected capabilities, decisions,
incidents, and resource evidence. It excludes packaging, raw paths, and report
prose.

`currentness_root` additionally hashes exact product, report, and resource owner/
file identities, the tracker byte hash, repository root identity, supervision
sources, and range head. It can change without inventing semantic novelty.

`artifact_root` hashes the exact packet without `artifact_root`. Identical
inputs produce byte-identical canonical JSON and the same packet ID. Packet
verification recomputes the roots and rejects extra keys or forbidden retained
content.

## Output and unchanged path

The output packet has exactly the fields frozen for
`product-program-evidence-packet`. Source records retain source IDs, path hashes,
byte hashes, byte lengths, and evidence classes; they contain no copied bytes.

When both the prior/current material fingerprints and prior/current currentness
roots match, the CLI returns `action: continue-program-unchanged`, `changed:
false`, `model_calls: 0`, and the verified packet. The comparison is constant
time after current identity preparation and invokes no semantic stage.

## Stop and negative posture

Stop before interpreting the packet. Reject stale tracker/range/repository
identity, target mismatch, root substitution, symlink/unbounded input, hidden or
raw-content fields, absent resource evidence class, or caller-asserted authority.
The packet itself states `derived-nonauthorizing` and `direct_effects_allowed:
false`.
