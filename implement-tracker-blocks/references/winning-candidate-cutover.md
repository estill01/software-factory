# Winning-candidate cutover

Use this contract only after Block 6 emits the exact accepted non-mutating
handoff for a `candidate-better` disposition. The incumbent stays authoritative
until the normal target owner completes the atomic integration commit.

## Required input and ownership

- Revalidate the sealed Block 6 review, accepted lane head, candidate bytes,
  comparison, protected capabilities, resource root, and handoff root.
- Resolve mission, policy, event head, tracker bytes, Block 9 contract, target
  Git head, affected bytes, and target-state root through the current owner at
  the write boundary. Caller-supplied roots are not currentness evidence.
- Require the handoff target owner, cutover owner, and actual Git writer to be
  the same existing owner. The handoff itself carries no cutover authority.
- If the Block 9 contract changed, return the exact structural effect to Block
  8 before any target write.

## Atomic integration and recovery

The target owner commits the candidate bytes and one `effect-pending` cutover
record together. The commit preserves the incumbent in Git history, marks it
superseded and non-authoritative, and marks the candidate as the sole active
implementation. Unrelated staged, unstaged, and untracked work remains intact.

Before the target ref changes, any failure restores the prior affected bytes
and leaves no cutover record. After the integration commit, retry resumes only
the missing current-effect proof. It never integrates a second time. A second
different handoff while the first is authoritative rejects.

## Selective currentness and continuation

Invalidate exactly proof whose subject is the superseded incumbent plus its
declared descendants. Preserve candidate validation, independent review,
policy, tracker, unrelated work, and every proof outside that closure. Do not
rerun their producers.

Execute the retained observable workload against the committed target bytes.
Require the exact artifact size, semantic roundtrip, bytes API, and protected
capability results accepted by Block 6. Until that proof is current, the
decision remains `effect-pending` and no resume token exists.

The accepted effect produces one deterministic resume token bound to the
handoff, integration commit, and effect root. The executor claims the token in
one target-owner record before starting the continuation; a repeated claim is
a no-op. Replaying the cutover returns the same token and performs no
integration, review, invalidation, or effect producer twice. Continuation stays
inside Block 9 until its audit accepts the current effect; no human Resume,
tracker amendment, release, publication, policy change, or Software Factory
self-target promotion is authorized.
