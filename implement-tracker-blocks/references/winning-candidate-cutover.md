# Winning-candidate cutover

Use this contract only after Block 6 emits the exact accepted non-mutating
handoff for a `candidate-better` disposition. The incumbent stays authoritative
until the normal target owner completes the atomic integration commit.

## Required input and ownership

- Revalidate the sealed Block 6 review, accepted lane head, candidate bytes,
  comparison, protected capabilities, resource root, and handoff root.
- Resolve mission, policy, event-ledger head, owner-root head, tracker program,
  target Git head, affected bytes, and target proof graph from canonical
  supervision and target owners. Hold both owner locks through promotion.
- Rehydrate the accepted logical target revision and isolated candidate path
  into an explicit current target/path mapping. The handoff and an input
  callback carry no target-write ownership.
- Freeze a detached candidate/proof commit, its exact parent, changed paths,
  binary-diff root, target mapping, supervision roots, program root, and proof
  transition in one proposal. A distinct sealed reviewer must accept that exact
  proposal with zero findings before the target ref can move.
- If any reviewed current or future Block contract changed, return the exact
  structural effect to Block 8 before any target write.

## Atomic integration and recovery

The target owner promotes only the reviewed detached commit. It contains the
candidate and the target-owned selective proof transition, preserves the
incumbent as its parent, and leaves unrelated staged, unstaged, and untracked
work intact. An affected staged or worktree change rejects before preparation
or promotion.

Before the target ref changes, every exception class restores the prior bytes
and caller index. After ref promotion, retry revalidates the signed proposal,
current committed bytes, target proof, and missing effect outcome. It never
creates a second integration. A failed effect rolls back only the exact
reviewed ref; a concurrent different commit is never labeled authoritative.

## Selective currentness and continuation

Read current proof from the target repository. Invalidate exactly current proof
whose subject is the superseded incumbent plus its declared descendants, and
bind the before/after roots in both proposal and review. Preserve candidate
validation, policy, tracker, unrelated work, and proof outside that closure.

Rehydrate the source from the current Git commit and execute the retained
observable workload against those bytes. Recheck the target ref, worktree,
proof, policy, mission, and event head after execution.
Require the exact artifact size, semantic roundtrip, bytes API, and protected
capability results accepted by Block 6. Until that proof is current, the
decision remains pending and no continuation execution key exists.

The accepted effect produces one deterministic execution key bound to the
handoff, reviewed commit, integration review, and effect root. Replaying the
cutover rehydrates the same executable next action and key without another
integration or proof transition. The downstream executor deduplicates by that
key; an interrupted return therefore cannot suppress continuation. No human
Resume, tracker amendment, release, publication, policy change, or Software
Factory self-target promotion is authorized.
