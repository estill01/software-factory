# Winning-candidate cutover

Use this contract only after Block 6 emits the exact accepted non-mutating
handoff for a `candidate-better` disposition. The incumbent stays authoritative
until the normal target owner completes the atomic integration commit.

## Required input and ownership

- Revalidate the sealed Block 6 review, accepted lane head, candidate bytes,
  comparison, protected capabilities, resource root, and handoff root.
- Resolve mission, policy, event-ledger head, owner-root head, tracker program,
  policy-owned implementation range, target Git head, affected bytes, and
  target proof graph from canonical supervision and target owners. Block 9
  must be the one current eligible range frontier. Hold both owner locks through
  promotion.
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

Before the target ref changes, compare-and-swap replacement rejects changed
affected bytes without overwriting them, and every exception class restores
only bytes still owned by the operation plus the prior caller index. Recovery
is independent per affected path: a changed, symlinked, or otherwise
caller-owned path is preserved without preventing restoration and index reset
for every other operation-owned path. Snapshot the exact affected index, hold
Git's index ownership lock across reviewed ref promotion, build the successor
index off-path, and publish it only through an exact-byte compare-and-swap.
Later staged/index state is caller-owned and must never be reset; compare
affected entries independently so unrelated staging does not suppress owned
entry recovery. If another owner advances the ref before or after promotion,
preserve that ref and restore each still-operation-owned worktree/index path,
including its regular/executable/symlink mode, against the actual surviving
tree. Apply the same compare-and-swap recovery after ref promotion so later
caller bytes are never overwritten. After ref
promotion, retry revalidates the signed proposal, current committed bytes,
target proof, retained review, and missing effect outcome. It never creates a
second integration. A failed effect rolls back only the exact reviewed ref; a
concurrent different commit is never labeled authoritative.

## Selective currentness and continuation

Read current proof from the target repository. Invalidate exactly current proof
whose subject is the superseded incumbent plus its declared descendants, and
bind the before/after roots in both proposal and review. Preserve candidate
validation, policy, tracker, unrelated work, and proof outside that closure.
Reject a graph that labels proof current while any dependency is stale.

Rehydrate the source from the current Git commit and execute the observable
workload once against those bytes. Persist and directory-sync its complete
rooted result in an operation spool before the final effect record, later
outcome, or continuation transition. Sign the spool/result with the separately
retained canonical owner-root key; a caller-created self-rooted record is not
producer provenance. A failed final record write rehydrates the owner-signed
spool without another workload run. That retained current-effect validation is
the first safe Block 9 continuation action. Recheck the target ref, worktree,
proof, full tracker program,
policy-owned range, policy, mission, and event head after execution. Retain and
revalidate the exact review and outcome; interruption or replay must rehydrate
the retained result and must not rerun the workload.
Require the exact artifact size, semantic roundtrip, bytes API, and protected
capability results accepted by Block 6. Until that proof is current, the
decision remains pending and no continuation execution key exists.

The accepted retained effect produces one deterministic execution key bound to
the handoff, reviewed commit, integration review, effect root, and current
range. After that first action actually completed, the cutover owner appends
the canonical supervision `work-started` successor transition with the exact
effect result as concrete start evidence. Replaying the cutover rehydrates that
same continuation root, next action, and key with `start_count=1`, without
another integration, proof transition, or workload execution. A final
target/proof/program/supervision comparison surrounds the transition write. If
state changes during the append, immediately append the canonical `corrected`
disposition against that exact `work-started` record so the successor gate
cannot continue stale work. No human Resume, tracker
amendment, release, publication, policy change, or Software Factory self-target
promotion is authorized.
