# Evidence and status rules

## Status vocabulary

Prefer a small vocabulary defined once by the tracker. A useful default is:

- `not-started`
- `in-progress`
- `completed-with-open-items`
- `accepted`
- `stale`
- `reopened`
- `blocked`

Use `complete` only when an inherited tracker already distinguishes it from
`accepted`. Keep the status table and each block's status line identical.

`completed-with-open-items` is not acceptance. A required independent review,
blocking finding, unresolved dependency, reserved decision, missing migration,
or absent exact evidence remains explicit.

## Completion evidence

For an implemented block, record the applicable subset of:

- exact repository commit and branch;
- external or domain revision/root;
- input paths, record IDs, versions, and hashes;
- output paths, record IDs, versions, and hashes;
- migrations, compatibility, and rollback posture;
- focused and mapped validation commands with results;
- changed-test selection and any justified widening;
- provider/model/resource use and declared ceilings;
- independent review identity, evidence hash, findings, and corrected-revision
  recheck;
- retained open work and explicit exclusions;
- post-block audit disposition;
- push or remote-durability posture when repository policy requires it.

Use `not-applicable` with a short reason rather than deleting an evidence field
whose absence could be mistaken for omission. Before implementation, write
`Pending.` rather than inventing evidence.

## Currentness and remediation

- Bind an acceptance claim to the exact implementation revision it reviewed.
- If a dependency changes, stale only mapped evidence where the architecture
  supports selective currentness.
- Preserve historical evidence append-only.
- Correct a rejected candidate in a later commit and obtain a fresh exact-commit
  review.
- Do not cite a pre-correction test or review as proof of a changed candidate.
- Freeze the candidate commit or content root before acceptance validation and
  exact-revision review. If the candidate changes during or after a run, retain
  that run as diagnostic evidence and rerun only the affected mapped proof.
- For a rejected candidate, record a compact closure matrix from each finding to
  its exact change, focused regression, mapped proof, and fresh review. Do not
  rerun unrelated broad validation merely because one finding changed.
- A docs-only evidence update may record an accepted implementation, but it
  cannot create acceptance that the implementation and review did not earn.

## Proof boundaries

Mechanical checks establish only the invariants they inspect. Schema validity,
hash agreement, file existence, mapping population, test success, or model
agreement do not by themselves establish substantive quality, legal status,
release readiness, or user approval.

An independent reviewer should be different from the treatment author when the
tracker requires independence. Reviewer identity is a review-separation fact,
not an access-control or multi-user feature.
